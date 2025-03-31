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

