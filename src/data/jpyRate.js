export const JPY_RATE = 158.92;
export function toJPY(usd) {
  return Math.round(usd * JPY_RATE).toLocaleString();
}
