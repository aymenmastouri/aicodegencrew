import { Injectable } from '@angular/core';

const DB_NAME = 'knowledge-artifacts';
const STORE_NAME = 'files';
const DB_VERSION = 1;
const MAX_CACHE_BYTES = 100 * 1024 * 1024; // 100 MB

interface CacheEntry {
  key: string; // runId/path
  content: string;
  size: number;
  cachedAt: number;
}

@Injectable({ providedIn: 'root' })
export class ArtifactCacheService {
  private db: IDBDatabase | null = null;
  private opening: Promise<IDBDatabase> | null = null;

  private open(): Promise<IDBDatabase> {
    if (this.db) return Promise.resolve(this.db);
    if (this.opening) return this.opening;

    this.opening = new Promise<IDBDatabase>((resolve, reject) => {
      const req = indexedDB.open(DB_NAME, DB_VERSION);
      req.onupgradeneeded = () => {
        const db = req.result;
        if (!db.objectStoreNames.contains(STORE_NAME)) {
          const store = db.createObjectStore(STORE_NAME, { keyPath: 'key' });
          store.createIndex('cachedAt', 'cachedAt', { unique: false });
        }
      };
      req.onsuccess = () => {
        this.db = req.result;
        this.opening = null;
        resolve(this.db);
      };
      req.onerror = () => {
        this.opening = null;
        reject(req.error);
      };
    });
    return this.opening;
  }

  async get(runId: string, path: string): Promise<string | null> {
    try {
      const db = await this.open();
      return new Promise((resolve) => {
        const tx = db.transaction(STORE_NAME, 'readonly');
        const req = tx.objectStore(STORE_NAME).get(`${runId}/${path}`);
        req.onsuccess = () => {
          const entry = req.result as CacheEntry | undefined;
          resolve(entry?.content ?? null);
        };
        req.onerror = () => resolve(null);
      });
    } catch {
      return null;
    }
  }

  async put(runId: string, path: string, content: string): Promise<void> {
    try {
      const db = await this.open();
      const entry: CacheEntry = {
        key: `${runId}/${path}`,
        content,
        size: content.length,
        cachedAt: Date.now(),
      };
      const tx = db.transaction(STORE_NAME, 'readwrite');
      tx.objectStore(STORE_NAME).put(entry);
      // Evict old entries if over limit (fire-and-forget)
      this.evictIfNeeded().catch(() => {});
    } catch {
      // Ignore cache write failures
    }
  }

  async getSize(): Promise<number> {
    try {
      const db = await this.open();
      return new Promise((resolve) => {
        const tx = db.transaction(STORE_NAME, 'readonly');
        const store = tx.objectStore(STORE_NAME);
        const req = store.openCursor();
        let total = 0;
        req.onsuccess = () => {
          const cursor = req.result;
          if (cursor) {
            total += (cursor.value as CacheEntry).size;
            cursor.continue();
          } else {
            resolve(total);
          }
        };
        req.onerror = () => resolve(0);
      });
    } catch {
      return 0;
    }
  }

  async clear(): Promise<void> {
    try {
      const db = await this.open();
      const tx = db.transaction(STORE_NAME, 'readwrite');
      tx.objectStore(STORE_NAME).clear();
    } catch {
      // Ignore
    }
  }

  private async evictIfNeeded(): Promise<void> {
    const size = await this.getSize();
    if (size <= MAX_CACHE_BYTES) return;

    const db = await this.open();
    const tx = db.transaction(STORE_NAME, 'readwrite');
    const store = tx.objectStore(STORE_NAME);
    const index = store.index('cachedAt');
    const req = index.openCursor();
    let remaining = size;

    req.onsuccess = () => {
      const cursor = req.result;
      if (cursor && remaining > MAX_CACHE_BYTES * 0.8) {
        remaining -= (cursor.value as CacheEntry).size;
        cursor.delete();
        cursor.continue();
      }
    };
  }
}
