#!/usr/bin/env python3
"""
Image pipeline: download product images, remove watermark, serve locally.

Usage:
  python3 image_pipeline.py <input_json_with_urls> [output_dir]
  
  python3 image_pipeline.py --process-url <image_url> [output_filename]

The script:
  1. Reads image URLs from products.json (or processes single URL)
  2. Downloads each image
  3. Detects and removes "CreationWatches" watermark
  4. Saves clean image to output directory
"""

import sys
import os
import json
import urllib.request
import io
import hashlib
from PIL import Image, ImageFilter


def detect_watermark_region(img):
    """Find the watermark region by looking for repeated gray text patterns."""
    if img.mode != "RGB":
        img = img.convert("RGB")
    pixels = img.load()
    w, h = img.size
    
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
            if total_width > 40:
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
    
    best_group = max(groups, key=lambda g: sum(r[2] for r in g))
    y1 = best_group[0][0]
    y2 = best_group[-1][0]
    
    x_min = img.width
    x_max = 0
    for row in best_group:
        for s, e, _ in row[1]:
            x_min = min(x_min, s)
            x_max = max(x_max, e)
    
    pad = 10
    return (max(0, x_min - pad), min(img.width, x_max + pad), 
            max(0, y1 - 2), min(img.height, y2 + 2))


def remove_watermark(img, region=None):
    """Remove watermark from image. Returns cleaned image."""
    if img.mode != "RGB":
        img = img.convert("RGB")
    
    if region is None:
        region = detect_watermark_region(img)
        if region is None:
            return img
    
    x1, x2, y1, y2 = region
    result = img.copy()
    pixels = result.load()
    
    # Collect non-watermark source pixels from within the region
    source_pixels = []
    for y in range(y1, y2):
        for x in range(x1, x2):
            r, g, b = img.getpixel((x, y))
            avg = (r + g + b) // 3
            if not (100 < avg < 230 and abs(r-g) < 25 and abs(g-b) < 25):
                source_pixels.append((r, g, b))
    
    if not source_pixels:
        return result
    
    # Replace watermark pixels with nearby non-watermark pixels
    for y in range(y1, y2):
        for x in range(x1, x2):
            r, g, b = pixels[x, y]
            avg = (r + g + b) // 3
            is_watermark = 100 < avg < 230 and abs(r-g) < 25 and abs(g-b) < 25
            
            if is_watermark:
                replacement = None
                # Search right
                for nx in range(x+1, x2):
                    nr, ng, nb = pixels[nx, y]
                    navg = (nr + ng + nb) // 3
                    if not (100 < navg < 230 and abs(nr-ng) < 25 and abs(ng-nb) < 25):
                        replacement = (nr, ng, nb)
                        break
                # Search left
                if replacement is None:
                    for nx in range(x-1, x1-1, -1):
                        nr, ng, nb = pixels[nx, y]
                        navg = (nr + ng + nb) // 3
                        if not (100 < navg < 230 and abs(nr-ng) < 25 and abs(ng-nb) < 25):
                            replacement = (nr, ng, nb)
                            break
                # Fallback
                if replacement is None:
                    replacement = source_pixels[0]
                
                pixels[x, y] = replacement
    
    # Light blur for smoothing
    reg = result.crop((x1, y1, x2, y2))
    blurred = reg.filter(ImageFilter.GaussianBlur(radius=0.5))
    result.paste(blurred, (x1, y1))
    
    return result


def process_image(image_url, output_path=None, images_dir=None):
    """
    Download image, remove watermark, save clean version.
    
    Args:
        image_url: URL of the image to process
        output_path: Full output path (or None to auto-generate)
        images_dir: Directory for auto-generated filenames
    
    Returns:
        (success, output_path_or_reason)
    """
    try:
        # Download
        data = urllib.request.urlopen(image_url, timeout=30).read()
        img = Image.open(io.BytesIO(data)).convert("RGB")
        
        # Remove watermark
        cleaned = remove_watermark(img)
        
        # Determine output path
        if output_path is None:
            if images_dir is None:
                return (False, "Must specify output_path or images_dir")
            
            # Generate filename from URL hash
            url_hash = hashlib.md5(image_url.encode()).hexdigest()[:12]
            ext = os.path.splitext(image_url.split("?")[0])[1] or ".webp"
            output_path = os.path.join(images_dir, f"{url_hash}{ext}")
        
        # Save (use PNG for quality)
        base, ext = os.path.splitext(output_path)
        if ext.lower() in ('.jpg', '.jpeg'):
            cleaned.save(output_path, "JPEG", quality=95)
        else:
            cleaned.save(output_path, "PNG")
        
        filesize = os.path.getsize(output_path)
        return (True, output_path, filesize)
    
    except Exception as e:
        return (False, str(e))


def process_batch(json_path, output_dir):
    """Process all images from products.json."""
    os.makedirs(output_dir, exist_ok=True)
    
    with open(json_path, "r") as f:
        products = json.load(f)
    
    updated_products = []
    success_count = 0
    fail_count = 0
    
    for i, product in enumerate(products):
        image_url = product.get("image", "")
        if not image_url:
            updated_products.append(product)
            continue
        
        # Generate output filename
        ext = os.path.splitext(image_url.split("?")[0])[1] or ".webp"
        url_hash = hashlib.md5(image_url.encode()).hexdigest()[:12]
        local_name = f"{url_hash}.png"
        output_path = os.path.join(output_dir, local_name)
        
        if os.path.exists(output_path):
            # Already processed, update the image field
            product["image_local"] = local_name
            updated_products.append(product)
            continue
        
        result = process_image(image_url, output_path)
        if result[0]:
            success_count += 1
            product["image_local"] = local_name
            print(f"  [{i+1}/{len(products)}] ✓ {local_name} ({result[2]/1024:.0f} KB)")
        else:
            fail_count += 1
            print(f"  [{i+1}/{len(products)}] ✗ {product.get('sku', '?')}: {result[1]}", file=sys.stderr)
        
        updated_products.append(product)
        
        # Be respectful - short delay
        # time.sleep(0.1)
    
    # Save updated products JSON with local image references
    output_json = os.path.join(output_dir, "products_clean.json")
    with open(output_json, "w") as f:
        json.dump(updated_products, f, indent=2, ensure_ascii=False)
    
    print(f"\nDone: {success_count} processed, {fail_count} failed")
    print(f"Updated products saved to: {output_json}")
    
    return success_count


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    if sys.argv[1] == "--process-url":
        url = sys.argv[2]
        output = sys.argv[3] if len(sys.argv) > 3 else None
        result = process_image(url, output)
        if result[0]:
            print(f"✓ Saved to: {result[1]}")
            print(f"  Size: {result[2]/1024:.0f} KB")
        else:
            print(f"✗ Failed: {result[1]}", file=sys.stderr)
    
    elif sys.argv[1] == "--batch":
        json_path = sys.argv[2]
        output_dir = sys.argv[3] if len(sys.argv) > 3 else "images_clean"
        process_batch(json_path, output_dir)
    
    else:
        print("Usage:")
        print("  python3 image_pipeline.py --process-url <url> [output]")
        print("  python3 image_pipeline.py --batch <products.json> [output_dir]")


if __name__ == "__main__":
    main()
