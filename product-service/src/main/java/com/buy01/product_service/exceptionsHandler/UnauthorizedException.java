package com.buy01.product_service.exceptionsHandler;


public class UnauthorizedException extends RuntimeException {
    public UnauthorizedException(String msg){
        super(msg);
    }
}
