export const getBubbleColor = (count: number) => {
  if (count > 100) return 'text-green-400';
  if (count > 50) return 'text-yellow-400';
  if (count > 10) return 'text-orange-400';
  return 'text-red-400';
};

export const getBubbleStatus = (count: number) => {
  if (count > 100) return '풍부함';
  if (count > 50) return '적정';
  if (count > 10) return '리필 권장';
  return '위험';
};