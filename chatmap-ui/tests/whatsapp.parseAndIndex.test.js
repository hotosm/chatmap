import { expect, test as it} from 'vitest'

import { howManyChanged, parseAndIndex } from '../src/components/ChatMap/parsers/whatsapp';

it('should count properly how many parts of two array differ', () => {
  var indexes = howManyChanged([1, 2, 3], [1, 2, 3]);
  expect(indexes).toEqual([]);
  var indexes = howManyChanged([1, 3, 3], [1, 2, 3]);
  expect(indexes).toEqual([1]);
  var indexes = howManyChanged([4, 3, 3], [1, 2, 3]);
  expect(indexes).toEqual([0, 1]);
  var indexes = howManyChanged([1, 1, 1], [2, 2, 2]);
  expect(indexes).toEqual([0, 1, 2]);
});

it('should parse a message for the Android system', () => {
  const msgs = [
    "17/10/2024, 3:37 p. m. - silvi: Necesito ayuda aquí!",
  ];

  const msgObjects = parseAndIndex(msgs, "ANDROID");

  expect(msgObjects[0].message).toEqual("Necesito ayuda aquí!");
});

it('should parse a message for the iOS system (multiple : characters)', () => {
  const msgs = [
    "[09/01/2025 12:50:14] Salomon: Name: Bentenie Type: Tree 🌳 Year: 2025",
  ];

  const msgObjects = parseAndIndex(msgs, "IOS");

  expect(msgObjects[0].message).toEqual("Name: Bentenie Type: Tree 🌳 Year: 2025");
});

it('should parse a message for the Android system (multiple : characters)', () => {
  const msgs = [
    "17/10/2024, 3:37 p. m. - Salomon: Name: Bentenie Type: Tree 🌳 Year: 2025",
  ];

  const msgObjects = parseAndIndex(msgs, "ANDROID");

  expect(msgObjects[0].message).toEqual("Name: Bentenie Type: Tree 🌳 Year: 2025");
});

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

it("should understand dates correctly when date doesn't change", () => {
  const msgs = [
    "3/4/25 17:29 - person: hi",
    "3/4/25 17:29 - person: hi",
  ];

  const msgObjects = parseAndIndex(msgs, "ANDROID");

  expect(msgObjects[0].time).toEqual(new Date('2025-03-04T17:29:00.000Z'));
  expect(msgObjects[1].time).toEqual(new Date('2025-03-04T17:29:00.000Z'));
});

it('should understand dates correctly when there is a day change', () => {
  const msgs = [
    "11/12/25 17:29 - person: hi",
    "12/12/25 17:29 - person: hi",
  ];

  const msgObjects = parseAndIndex(msgs, "ANDROID");

  expect(msgObjects[0].time).toEqual(new Date('2025-12-11T17:29:00.000Z'));
  expect(msgObjects[1].time).toEqual(new Date('2025-12-12T17:29:00.000Z'));
});

it('no matter where it happens', () => {
  const msgs = [
    "12/12/25 17:29 - person: hi",
    "12/13/25 17:29 - person: hi",
  ];

  const msgObjects = parseAndIndex(msgs, "ANDROID");

  expect(msgObjects[0].time).toEqual(new Date('2025-12-12T17:29:00.000Z'));
  expect(msgObjects[1].time).toEqual(new Date('2025-12-13T17:29:00.000Z'));
});

it('should understand dates correctly when there is a month change', () => {
  const msgs = [
    "31/1/25 17:29 - person: hi",
    "1/2/25 17:29 - person: hi",
  ];

  const msgObjects = parseAndIndex(msgs, "ANDROID");

  expect(msgObjects[0].time).toEqual(new Date('2025-01-31T17:29:00.000Z'));
  expect(msgObjects[1].time).toEqual(new Date('2025-02-01T17:29:00.000Z'));
});

it('should understand dates correctly when there is a year change', () => {
  const msgs = [
    "12/12/25 17:29 - person: hi",
    "5/1/26 17:29 - person: hi",
    "5/2/26 17:29 - person: hi",
  ];

  const msgObjects = parseAndIndex(msgs, "ANDROID");

  expect(msgObjects[0].time).toEqual(new Date('2025-12-12T17:29:00.000Z'));
  expect(msgObjects[1].time).toEqual(new Date('2026-05-01T17:29:00.000Z'));
  expect(msgObjects[2].time).toEqual(new Date('2026-05-02T17:29:00.000Z'));
});

it('should understand times with am/pm', () => {
  const msgs = [
    "12/12/25 03:29 a.m. - person: hi",
    "12/12/25 03:29 p.m. - person: hi",
  ];

  const msgObjects = parseAndIndex(msgs, "ANDROID");

  expect(msgObjects[0].time).toEqual(new Date('2025-12-12T03:29:00.000Z'));
  expect(msgObjects[1].time).toEqual(new Date('2025-12-12T15:29:00.000Z'));
});

it('should work with this', () => {
  const msgs = [
    "[09/12/2024, 03:05:52] Emi: <attached: 00000002-PHOTO-2024-12-09-03-05-52.jpg>",
    "[10/12/2024, 16:55:32] Emi: Location: https://maps.google.com/?q=-34.816833,-58.541428",
    "[12/12/2024, 23:21:16] Emi: <attached: 00000020-GIF-2024-12-12-23-21-16.mp4>",
    "[27/12/2024, 08:38:27] Emi: Location: https://maps.google.com/?q=-31.044813,-64.276016",
    "[31/12/2024, 11:35:11] Emi: <attached: 00000029-PHOTO-2024-12-31-11-35-11.jpg>",
  ];

  const msgObjects = parseAndIndex(msgs, "IOS");

  expect(msgObjects[0].time).toEqual(new Date('2024-12-09T03:05:52.000Z'));
});

it('should work with that', () => {
  const msgs = [
    "12/08/25 09.47 - BPBD Pika: lokasi : https://maps.google.com/?q=-8.4475246,115.5904475",
  ];

  const msgObjects = parseAndIndex(msgs, "ANDROID");

  expect(msgObjects[0].time).toEqual(new Date('2025-12-08T09:47:00.000Z'));
});
