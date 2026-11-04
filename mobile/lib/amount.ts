/** "1 1/2 su bardağı", "2-3 diş", "500 g", "1/2 demet" gibi malzeme miktarlarındaki baştaki sayıyı çarpanla ölçekler. */
const FRACTIONS: [number, string][] = [[0.25, '¼'], [0.5, '½'], [0.75, '¾']];

function format(value: number): string {
  if (value >= 10) return String(Math.round(value));
  const whole = Math.floor(value + 1e-9);
  const rest = value - whole;
  const near = FRACTIONS.find(([f]) => Math.abs(rest - f) < 0.06);
  if (rest < 0.06) return String(whole);
  if (rest > 0.94) return String(whole + 1);
  if (near) return whole > 0 ? `${whole} ${near[1]}` : near[1];
  return (Math.round(value * 10) / 10).toString().replace('.', ',');
}

const num = (s: string) => Number(s.replace(',', '.'));

export function scaleAmount(text: string, factor: number): string {
  if (!text || Math.abs(factor - 1) < 1e-9) return text;
  // 1 1/2  |  1/2  |  2-3  |  1,5  |  500
  const re = /^(?:(\d+)\s+(\d+)\/(\d+)|(\d+)\/(\d+)|(\d+(?:[.,]\d+)?)(?:\s*[-–]\s*(\d+(?:[.,]\d+)?))?)/;
  const m = re.exec(text.trim());
  if (!m) return text;
  const rest = text.trim().slice(m[0].length);
  if (m[1]) return format((Number(m[1]) + Number(m[2]) / Number(m[3])) * factor) + rest;
  if (m[4]) return format((Number(m[4]) / Number(m[5])) * factor) + rest;
  const low = format(num(m[6]) * factor);
  return (m[7] ? `${low}-${format(num(m[7]) * factor)}` : low) + rest;
}
