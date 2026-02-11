import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface InputFile {
  filename: string;
  size_bytes: number;
  modified: string;
  extension: string;
}

export interface CategoryDetail {
  label: string;
  description: string;
  icon: string;
  env_key: string;
  accepted_extensions: string[];
  files: InputFile[];
  file_count: number;
  total_size: number;
}

export interface InputsSummary {
  categories: Record<string, { label: string; icon: string; file_count: number; total_size: number }>;
  total_files: number;
  total_size: number;
}

export interface CategoryMeta {
  id: string;
  label: string;
  description: string;
  icon: string;
  env_key: string;
  accepted_extensions: string[];
}

@Injectable({ providedIn: 'root' })
export class InputsService {
  private base = '/api/inputs';

  constructor(private http: HttpClient) {}

  listAll(): Observable<Record<string, CategoryDetail>> {
    return this.http.get<Record<string, CategoryDetail>>(this.base);
  }

  getSummary(): Observable<InputsSummary> {
    return this.http.get<InputsSummary>(`${this.base}/summary`);
  }

  getCategories(): Observable<CategoryMeta[]> {
    return this.http.get<CategoryMeta[]>(`${this.base}/categories`);
  }

  listCategory(category: string): Observable<InputFile[]> {
    return this.http.get<InputFile[]>(`${this.base}/${category}`);
  }

  uploadFile(category: string, file: File): Observable<{ filename: string; category: string; size_bytes: number }> {
    const formData = new FormData();
    formData.append('file', file);
    return this.http.post<{ filename: string; category: string; size_bytes: number }>(
      `${this.base}/${category}/upload`,
      formData,
    );
  }

  deleteFile(category: string, filename: string): Observable<{ success: boolean; message: string }> {
    return this.http.delete<{ success: boolean; message: string }>(
      `${this.base}/${category}/${encodeURIComponent(filename)}`,
    );
  }
}
