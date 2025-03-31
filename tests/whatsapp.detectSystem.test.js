import { expect, test as it} from 'vitest'

import { detectSystem } from '../src/parsers/whatsapp';

// detectSystem

it('should detect the Android system', () => {
  const message = "16/10/2024, 7:41 p. m. - Emi: 😊";
  const system = detectSystem(message);
  expect(system).toEqual("ANDROID"); 
});

it('should detect the iOS system', () => {
  const message = "[07/01/25, 1:52:56 p.m.] La M: ‎Añadiste a La M.";
  const system = detectSystem(message);
  expect(system).toEqual("IOS"); 
});
