export const getBubbleColor = (count: number) => {
  if (count > 750) return 'text-green-400';
  if (count > 500) return 'text-yellow-400';
  if (count > 250) return 'text-orange-400';
  return 'text-red-400';
};

export const getBubbleStatus = (count: number) => {
  if (count > 750) return '풍부함';
  if (count > 500) return '보통';
  if (count > 250) return '부족';
  return '위험';
};