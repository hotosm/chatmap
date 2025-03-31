import { expect, test } from 'vitest'

import { searchLocation } from '../src/parsers/whatsapp';

test('should extract location coordinates correctly from a Google URL', () => {
  const message = "https://maps.google.com/?q=-1.12345,-48.12345";
  const location = searchLocation(message);
  expect(location).toEqual([-1.12345, -48.12345]); 
});

test('should extract location coordinates correctly from a string', () => {
  const message = "-1.12345,-48.12345";
  const location = searchLocation(message);
  expect(location).toEqual([-1.12345, -48.12345]); 
});


test('should extract location coordinates correctly from a GeoURI', () => {
  const message = "geoURI:-1.12345,-48.12345";
  const location = searchLocation(message);
  expect(location).toEqual([-1.12345, -48.12345]); 
});

test('should extract location coordinates (one positive, one negative', () => {
  const message = "1.12345,-48.12345";
  const location = searchLocation(message);
  expect(location).toEqual([1.12345,-48.12345]); 
});

test('should extract location coordinates (one negative, one positive', () => {
  const message = "-1.12345,48.12345";
  const location = searchLocation(message);
  expect(location).toEqual([-1.12345,48.12345]); 
});


// describe('detectSystem', () => {

//   it('should detect Android', () => {
//   });

//   it('should detect iOS', () => {
//   });

// });

// describe('lookForMediaFile', () => {

//   it('should found a JPG image file', () => {
//   });

//   it('should found a MP4 video file', () => {
//   });

// });

// describe('parseDateStringiOS', () => {
//   it('should parse an iOS date string', () => {
//   });
// });

// describe('parseDateStringAndroid', () => {
//   it('should parse an Android date string', () => {
//   });
// });


// describe('parseMessage', () => {

//   it('should parse an iOS message', () => {
//   });

//   it('should parse an Android message', () => {
//   });

// });

// describe('parseAndIndex', () => {
//   it('should parse an index messages', () => {
//   });
// });

// describe('getClosestMessage', () => {
//   it('should get closest message (first location, then message)', () => {
//   });
//   it('should get closest message (first message, then location)', () => {
//   });
//   it('should get closest message (location only)', () => {
//   });
//   it('should get closest message (location last)', () => {
//   });
// })