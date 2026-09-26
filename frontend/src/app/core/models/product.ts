export interface Product {
    id?: string;
    name: string;
    description: string;
    price: number;
    ownerId?: string;
    images?: string[];
    mediaIds?: string[];
    createdAt?: string;
    quantity: number;
}
