package com.buy01.product_service.exception;

public class BadRequest extends RuntimeException {
    public BadRequest(String msg) {
        super(msg);
    }
}
