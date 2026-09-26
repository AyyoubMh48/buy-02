export type Role = 'CLIENT' | 'SELLER';

export interface User {
    id : string;
    email : string;
    fullName? : string;
    username? : string;
    role : Role;
    avatarUrl? : string;
}

export interface AuthResponse {
    token : string;
    user : User;
}

export interface RegisterRequest {
    email: string;
    password: string;
    fullName: string;
    role: Role;
    avatarUrl?: string;
}
