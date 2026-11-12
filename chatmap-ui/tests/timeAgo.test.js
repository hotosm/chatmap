import { expect, test as it} from 'vitest'

import { timeAgo } from '../src/components/TimeAgo';

const NOW = new Date("2026-10-06T12:00:00Z").getTime();

// timeAgo
it('should count minutes under an hour', () => {
  expect(timeAgo("2026-10-06T11:50:00Z", NOW)).toEqual({ value: -10, unit: "minute" });
});
it('should count hours under a day', () => {
  expect(timeAgo("2026-10-06T00:00:00Z", NOW)).toEqual({ value: -12, unit: "hour" });
});
it('should count days from a day on', () => {
  expect(timeAgo("2026-10-04T11:00:00Z", NOW)).toEqual({ value: -2, unit: "day" });
});
it('should be zero minutes for something that just happened', () => {
  expect(timeAgo("2026-10-06T11:59:40Z", NOW)).toEqual({ value: 0, unit: "minute" });
});
it('should return null for an invalid date', () => {
  expect(timeAgo("not a date", NOW)).toBeNull();
});
