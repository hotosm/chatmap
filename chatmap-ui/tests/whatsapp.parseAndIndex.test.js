import { expect, test as it} from 'vitest'

import { parseAndIndex } from '../src/components/ChatMap/parsers/whatsapp';

// parseAndIndex

it('should parse messages for the iOS system', () => {
  const msgs = ["[09/01/2025 12:50:14] Salomon: Name Bentenie Type Tree 🌳 Year 2025",
                "[09/01/2025 12:50:14] Salomon: Name: Bentenie Type: Tree 🌳 Year: 2025"];

  const msgObjects = parseAndIndex(msgs, "IOS");
  expect(msgObjects[0].message).toEqual("Name Bentenie Type Tree 🌳 Year 2025"); 
});

it('should parse multi-line messages', () => {
    const msgs = ["[09/01/2025 12:50:14] Salomon: hey dude",
                  "how are you?",
                  "all good?",
                  "[09/01/2025 12:50:14] This is a system message",
                  "[09/01/2025 12:50:14] Salomon: Name: Bentenie Type: Tree 🌳 Year: 2025"];
  
    const msgObjects = parseAndIndex(msgs, "IOS");
    expect(msgObjects[0].message).toEqual("hey dude how are you? all good?"); 
  });

it('should get datetimes correctly', () => {
});
