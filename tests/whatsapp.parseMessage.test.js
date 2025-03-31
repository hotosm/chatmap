import { expect, test as it} from 'vitest'

import { parseMessage } from '../src/parsers/whatsapp';

// parseMessage

it('should parse a message for the Android system', () => {
  const msgObject = parseMessage(
    "[09/01/2025 12:50:14] Salomon: Name Bentenie Type Tree 🌳 Year 2025",
    "IOS"
  );
  expect(msgObject.message).toEqual("Name Bentenie Type Tree 🌳 Year 2025"); 
});

it('should parse a message for the iOS system', () => {
  const msgObject = parseMessage(
    "17/10/2024, 3:37 p. m. - silvi: Necesito ayuda aquí!",
    "ANDROID"
  );
  expect(msgObject.message).toEqual("Necesito ayuda aquí!"); 
});

// FIXME
// it('should parse a message for the Android system (multiple : characters)', () => {
//   const msgObject = parseMessage(
//     "[09/01/2025 12:50:14] Salomon: Name: Bentenie Type: Tree 🌳 Year: 2025",
//     "IOS"
//   );
//   expect(msgObject.message).toEqual("Name: Bentenie Type: Tree 🌳 Year: 2025"); 
// });
