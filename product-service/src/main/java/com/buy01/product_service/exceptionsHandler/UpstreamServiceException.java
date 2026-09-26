package com.buy01.product_service.exceptionsHandler;


public class UpstreamServiceException extends RuntimeException {
    public UpstreamServiceException(String message) {
        super(message);
    }
}
