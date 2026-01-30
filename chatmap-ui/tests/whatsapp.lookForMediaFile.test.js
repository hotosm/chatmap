import { expect, test as it} from 'vitest'

import { lookForMediaFile } from '../src/components/ChatMap/parsers/whatsapp';

// lookForMediaFile

it('should find a video', () => {
  const { path, type } = lookForMediaFile({
    message: "‎[08/01/25, 1:48:18 p.m.] La M: ‎<adjunto: 00000005-VIDEO-2025-01-08-13-48-18.mp4>",
  });
  expect(path).toEqual("00000005-VIDEO-2025-01-08-13-48-18.mp4");
  expect(type).toEqual("video");
});
it('should find a picture', () => {
  const { path, type } = lookForMediaFile({
    message: "‎[09/01/2025 12:23:17] Salomon: ‎< pièce jointe : 00000005-PHOTO-2025-01-09-12-23-16.jpg >",
  });
  expect(path).toEqual("00000005-PHOTO-2025-01-09-12-23-16.jpg");
  expect(type).toEqual("image");
});
it('should find a picture (no space after :)', () => {
  const { path, type } = lookForMediaFile({
    message: "‎[09/01/2025 12:23:17] Salomon: ‎< pièce jointe :00000005-PHOTO-2025-01-09-12-23-16.jpg >",
  });
  expect(path).toEqual("00000005-PHOTO-2025-01-09-12-23-16.jpg");
  expect(type).toEqual("image");
});
