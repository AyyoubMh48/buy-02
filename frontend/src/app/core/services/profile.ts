import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { User } from '../models/user';
import { API_BASE_URL } from '../api-config';

export interface UpdateProfileRequest {
  username: string;
  avatarUrl?: string;
}

@Injectable({ providedIn: 'root' })
export class ProfileService {
  private readonly API_URL = `${API_BASE_URL}/me`;

  constructor(private readonly http: HttpClient) {}

  getProfile(): Observable<User> {
    return this.http.get<User>(this.API_URL);
  }

  updateProfile(request: UpdateProfileRequest): Observable<User> {
    return this.http.put<User>(this.API_URL, request);
  }
}