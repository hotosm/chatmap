import {createMaps} from './0001_create_maps';
import {createQueue} from './0002_create_queue';
import {addMediaCapturedAt} from './0003_add_media_captured_at';

// A phone records how many of these it already ran, so only append: never edit, remove or reorder one that shipped.
export const MIGRATIONS = [createMaps, createQueue, addMediaCapturedAt];
