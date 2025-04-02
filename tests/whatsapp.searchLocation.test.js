import { expect, test as it} from 'vitest'

import { searchLocation } from '../src/components/ChatMap/parsers/whatsapp';

// searchLocation

it('should extract location coordinates correctly from a Google URL', () => {
  const message = "My location is https://maps.google.com/?q=-1.12345,-48.12345";
  const location = searchLocation(message);
  expect(location).toEqual([-1.12345, -48.12345]); 
});

it('should extract location coordinates correctly from a string', () => {
  const message = "Lat/lon -1.12345,-48.12345";
  const location = searchLocation(message);
  expect(location).toEqual([-1.12345, -48.12345]); 
});

it('should extract location coordinates correctly from a GeoURI', () => {
  const message = "I'm here geoURI:-1.12345,-48.12345";
  const location = searchLocation(message);
  expect(location).toEqual([-1.12345, -48.12345]); 
});

it('should extract location coordinates (one positive, one negative)', () => {
  const message = "My coords 1.12345,-48.12345 I'm here";
  const location = searchLocation(message);
  expect(location).toEqual([1.12345, -48.12345]); 
});

it('should extract location coordinates (one negative, one positive)', () => {
  const message = "I'm here -1.12345,48.12345 please come";
  const location = searchLocation(message);
  expect(location).toEqual([-1.12345, 48.12345]); 
});

