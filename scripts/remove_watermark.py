#!/usr/bin/env python3
"""
remove_watermark.py — Remove "CreationWatches" watermark from product images.

Detection:
- Scans the bottom portion of images for semi-transparent gray text
- "CreationWatches" watermark appears around y=920-950 (for 1024x1024 images)
- Uses inpainting: replaces watermark pixels with estimated background

Usage:
  python3 remove_watermark.py <input_image> [output_image]
  python3 remove_watermark.py --batch <input_dir> [output_dir]
  python3 remove_watermark.py --url <image_url> [output_file]
"""

import sys
import os
import urllib.request
import io
from PIL import Image, ImageFilter
import json
import re

def detect_watermark_region(img):
    """Find the watermark region by looking for repeated gray text patterns."""
    if img.mode != "RGB":
        img = img.convert("RGB")
    pixels = img.load()
    w, h = img.size
    
    # Watermark is typically in the lower portion
    search_start = h - 250
    search_end = h - 20
    
    text_rows = []
    for y in range(search_start, search_end):
        text_pixels = []
        in_run = False
        run_start = 0
        for x in range(w // 2 - 200, w // 2 + 200):
            r, g, b = pixels[x, y]
            avg = (r + g + b) // 3
            # Watermark text: grayish pixels on lighter background
            is_graytext = 100 < avg < 230 and abs(r-g) < 25 and abs(g-b) < 25
            if is_graytext:
                if not in_run:
                    run_start = x
                    in_run = True
            else:
                if in_run:
                    run_width = x - run_start
                    if run_width >= 3:
                        text_pixels.append((run_start, x, run_width))
                    in_run = False
        if in_run:
            run_width = (w // 2 + 200) - run_start
            if run_width >= 3:
                text_pixels.append((run_start, w // 2 + 200, run_width))
        
        if text_pixels:
            total_width = sum(r[2] for r in text_pixels)
            if total_width > 40:  # Significant text = watermark
                text_rows.append((y, text_pixels, total_width))
    
    if not text_rows:
        return None
    
    # Group contiguous rows
    groups = []
    current = [text_rows[0]]
    for i in range(1, len(text_rows)):
        if text_rows[i][0] - text_rows[i-1][0] <= 2:
            current.append(text_rows[i])
        else:
            groups.append(current)
            current = [text_rows[i]]
    groups.append(current)
    
    # Find the largest group (most text pixels)
    best_group = max(groups, key=lambda g: sum(r[2] for r in g))
    
    y1 = best_group[0][0]
    y2 = best_group[-1][0]
    
    # Find x-bounds from the group
    x_min = w
    x_max = 0
    for row in best_group:
        for s, e, _ in row[1]:
            x_min = min(x_min, s)
            x_max = max(x_max, e)
    
    pad = 10  # Padding
    return (max(0, x_min - pad), min(w, x_max + pad), 
            max(0, y1 - 2), min(h, y2 + 2))


def remove_watermark(img, region=None, method="inpaint"):
    """
    Remove watermark from image.
    
    Args:
        img: PIL Image object (RGB)
        region: (x1, x2, y1, y2) tuple or None for auto-detect
        method: "inpaint" or "fill"
    
    Returns:
        PIL Image with watermark removed
    """
    if img.mode != "RGB":
        img = img.convert("RGB")
    
    if region is None:
        region = detect_watermark_region(img)
        if region is None:
            print("No watermark detected", file=sys.stderr)
            return img
    
    x1, x2, y1, y2 = region
    print(f"Watermark region: ({x1},{y1})-({x2},{y2})", file=sys.stderr)
    
    result = img.copy()
    pixels = result.load()
    
    if method == "fill":
        # Simple fill: replace each watermark pixel with the average of 
        # neighboring non-watermark pixels
        
        for y in range(y1, y2):
            for x in range(x1, x2):
                r, g, b = pixels[x, y]
                avg = (r + g + b) // 3
                is_watermark = 100 < avg < 230 and abs(r-g) < 25 and abs(g-b) < 25
                
                if is_watermark:
                    # Sample surrounding non-watermark pixels
                    neighbors = []
                    for dx, dy in [(0, -y1), (x2-x1, 0), (0, y2-y1), (-x1, 0),
                                   (-5, -3), (5, -3), (-5, 3), (5, 3)]:
                        nx, ny = x + dx, y + dy
                        if 0 <= nx < result.width and 0 <= ny < result.height:
                            nr, ng, nb = pixels[nx, ny]
                            navg = (nr + ng + nb) // 3
                            if not (100 < navg < 230 and abs(nr-ng) < 25 and abs(ng-nb) < 25):
                                neighbors.append((nr, ng, nb))
                    
                    if neighbors:
                        avg_r = sum(n[0] for n in neighbors) // len(neighbors)
                        avg_g = sum(n[1] for n in neighbors) // len(neighbors)
                        avg_b = sum(n[2] for n in neighbors) // len(neighbors)
                        pixels[x, y] = (avg_r, avg_g, avg_b)
    
    elif method == "inpaint":
        # Improved inpainting: replace watermark pixels by sampling
        # nearby non-watermark pixels from the same image
        
        # Build a list of non-watermark source pixels from the region
        source_pixels = []
        for y in range(y1, y2):
            for x in range(x1, x2):
                r, g, b = img.getpixel((x, y))
                avg = (r + g + b) // 3
                if not (100 < avg < 230 and abs(r-g) < 25 and abs(g-b) < 25):
                    source_pixels.append((r, g, b))
        
        if source_pixels:
            # For each watermark pixel, replace with closest non-watermark
            # pixel from the same row or nearby rows
            for y in range(y1, y2):
                for x in range(x1, x2):
                    r, g, b = pixels[x, y]
                    avg = (r + g + b) // 3
                    is_watermark = 100 < avg < 230 and abs(r-g) < 25 and abs(g-b) < 25
                    
                    if is_watermark:
                        # Find closest non-watermark pixel horizontally
                        replacement = None
                        
                        # Search right first
                        for nx in range(x+1, x2):
                            nr, ng, nb = pixels[nx, y]
                            navg = (nr + ng + nb) // 3
                            if not (100 < navg < 230 and abs(nr-ng) < 25 and abs(ng-nb) < 25):
                                replacement = (nr, ng, nb)
                                break
                        
                        # Search left if not found
                        if replacement is None:
                            for nx in range(x-1, x1-1, -1):
                                nr, ng, nb = pixels[nx, y]
                                navg = (nr + ng + nb) // 3
                                if not (100 < navg < 230 and abs(nr-ng) < 25 and abs(ng-nb) < 25):
                                    replacement = (nr, ng, nb)
                                    break
                        
                        # Fallback: use any nearby source pixel
                        if replacement is None:
                            replacement = source_pixels[len(source_pixels) // 2]
                        
                        pixels[x, y] = replacement
            
            # Apply a very light blur to smooth transitions
            reg = result.crop((x1, y1, x2, y2))
            blurred = reg.filter(ImageFilter.GaussianBlur(radius=0.5))
            result.paste(blurred, (x1, y1))
    
    return result


def process_directory(input_dir, output_dir=None):
    """Process all images in a directory."""
    if output_dir is None:
        output_dir = input_dir + "_clean"
    os.makedirs(output_dir, exist_ok=True)
    
    count = 0
    for fname in os.listdir(input_dir):
        if fname.lower().endswith(('.webp', '.jpg', '.jpeg', '.png')):
            inpath = os.path.join(input_dir, fname)
            outpath = os.path.join(output_dir, fname)
            
            try:
                img = Image.open(inpath).convert("RGB")
                region = detect_watermark_region(img)
                if region:
                    cleaned = remove_watermark(img, region, method="inpaint")
                    cleaned.save(outpath)
                    count += 1
                    print(f"  Cleaned: {fname}")
                else:
                    # No watermark, copy as-is
                    img.save(outpath)
                    print(f"  Skipped (no watermark): {fname}")
            except Exception as e:
                print(f"  ERROR: {fname}: {e}", file=sys.stderr)
    
    print(f"\nProcessed {count} images with watermarks")
    return count


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    if sys.argv[1] == "--batch":
        input_dir = sys.argv[2]
        output_dir = sys.argv[3] if len(sys.argv) > 3 else None
        process_directory(input_dir, output_dir)
    elif sys.argv[1] == "--url":
        url = sys.argv[2]
        output_path = sys.argv[3] if len(sys.argv) > 3 else "output.webp"
        
        data = urllib.request.urlopen(url).read()
        img = Image.open(io.BytesIO(data)).convert("RGB")
        cleaned = remove_watermark(img)
        cleaned.save(output_path)
        print(f"Saved to {output_path}")
    elif sys.argv[1] == "--test":
        # Test with a known creationwatches image
        test_urls = [
            "https://cdnstatic.creationwatches.com/products/product-images/l/GM-S2110SH-7A_LRG.webp",
            "https://cdnstatic.creationwatches.com/products/product-images/l/PRW-61ANS-3_LRG.webp",
        ]
        for url in test_urls:
            fname = url.split("/")[-1]
            print(f"\nTesting: {fname}")
            data = urllib.request.urlopen(url).read()
            img = Image.open(io.BytesIO(data)).convert("RGB")
            region = detect_watermark_region(img)
            if region:
                print(f"  Detected region: {region}")
                cleaned = remove_watermark(img, region)
                outpath = f"clean_{fname}"
                cleaned.save(outpath)
                print(f"  Saved: {outpath}")
            else:
                print("  No watermark detected")
    else:
        # Single file
        inpath = sys.argv[1]
        outpath = sys.argv[2] if len(sys.argv) > 2 else inpath
        
        img = Image.open(inpath).convert("RGB")
        cleaned = remove_watermark(img)
        cleaned.save(outpath)
        print(f"Saved to {outpath}")


if __name__ == "__main__":
    main()
