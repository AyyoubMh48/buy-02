package com.buy01.product_service.exceptionsHandler;

public class BadRequest extends RuntimeException {
    public BadRequest(String msg) {
        super(msg);
    }
}
