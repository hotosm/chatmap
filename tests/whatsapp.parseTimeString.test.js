import { expect, test as it} from 'vitest'

import { parseTimeString } from '../src/components/ChatMap/parsers/whatsapp';

// parseTimeString
it('should parse a datetime', () => {
  const dt = parseTimeString("17/10/2024, 3:37 p. m.")
  expect(dt.getHours()).toEqual(15); 
  expect(dt.getMinutes()).toEqual(37); 
});
it('should parse a datetime', () => {
  const dt = parseTimeString("09/01/2025 12:52:39")
  expect(dt.getHours()).toEqual(12); 
  expect(dt.getMinutes()).toEqual(52); 
});
