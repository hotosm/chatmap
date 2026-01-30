import { expect, test as it} from 'vitest'
import parser, { searchLocation } from '../src/components/ChatMap/parsers/whatsapp';
import ChatMap from '../src/components/ChatMap/chatmap';

it('should parse locations + messages from a chat', () => {
const text = ["[08/01/25, 6:02:14 p.m.] Ann: Look how nice",
            "[08/01/25, 6:02:15 p.m.] Ann: Location: https://maps.google.com/?q=20.672598,-100.446259",
            "[08/01/25, 6:06:12 p.m.] Ann: Point 1",
            "[08/01/25, 6:06:15 p.m.] Ann: Location: https://maps.google.com/?q=20.672564,-100.446259",
            "[08/01/25, 6:26:52 p.m.] Ann: Point 2",
            "[08/01/25, 6:27:00 p.m.] Ann: Location: https://maps.google.com/?q=20.672567,-100.446297",
            ].join("\n");
  const messages = parser({ text: text });
  const chatmap = new ChatMap(messages);
  const geoJSON = chatmap.pairContentAndLocations(searchLocation, {});
  expect(geoJSON.features.length).toEqual(3); 
});

it('should parse locations + messages from a chats with multi-lines', () => {
const text = ["[08/01/25, 6:02:14 p.m.] Ann: Another thing",
            "in multiline text",
            "[08/01/25, 6:02:15 p.m.] Ann: Magical Food",
            "Fake Street 1234",
            "Location: https://maps.google.com/?q=20.672598,-100.446259",
            "[08/01/25, 6:06:12 p.m.] Ann: Point A",
            "[08/01/25, 6:06:15 p.m.] Ann: Location: https://maps.google.com/?q=20.672564,-100.446259",
            "[08/01/25, 6:26:52 p.m.] Ann: Point B",
            "[08/01/25, 6:27:00 p.m.] Ann: Location: https://maps.google.com/?q=20.672567,-100.446297",
            ].join("\n");
  const messages = parser({ text: text });
  const chatmap = new ChatMap(messages);
  const geoJSON = chatmap.pairContentAndLocations(searchLocation, {});
  expect(geoJSON.features.length).toEqual(3); 
});
