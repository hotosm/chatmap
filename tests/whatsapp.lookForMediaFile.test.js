import { expect, test as it} from 'vitest'

import { lookForMediaFile } from '../src/parsers/whatsapp';

// lookForMediaFile

it('should found a video', () => {
  const filename = lookForMediaFile({
    message: "‎[08/01/25, 1:48:18 p.m.] La M: ‎<adjunto: 00000005-VIDEO-2025-01-08-13-48-18.mp4>",
  });
  expect(filename).toEqual("00000005-VIDEO-2025-01-08-13-48-18.mp4"); 
});
it('should found a picture', () => {
  const filename = lookForMediaFile({
    message: "‎[09/01/2025 12:23:17] Salomon: ‎< pièce jointe : 00000005-PHOTO-2025-01-09-12-23-16.jpg >",
  });
  expect(filename).toEqual("00000005-PHOTO-2025-01-09-12-23-16.jpg"); 
});

