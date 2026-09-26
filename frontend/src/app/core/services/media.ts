import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, throwError } from 'rxjs';
import { MediaResponse } from '../models/media';
import { API_BASE_URL } from '../api-config';

@Injectable({ providedIn: 'root' })
export class MediaService {
  private readonly API_URL = `${API_BASE_URL}/media`;
  readonly MAX_FILE_SIZE = 2 * 1024 * 1024; // 2 MB

  constructor(private http: HttpClient) {}

  uploadImage(file: File): Observable<MediaResponse> {
    if (!file.type.startsWith('image/')) {
      return throwError(() => new Error('Only image files (image/*) are permitted.'));
    }
    if (file.size > this.MAX_FILE_SIZE) {
      return throwError(() => new Error('File size exceeds the 2 MB limit.'));
    }

    const formData = new FormData();
    formData.append('file', file);

    return this.http.post<MediaResponse>(`${this.API_URL}/images`, formData);
  }

  getImageUrl(id: string): string {
    return `${this.API_URL}/images/${id}`;
  }
}
