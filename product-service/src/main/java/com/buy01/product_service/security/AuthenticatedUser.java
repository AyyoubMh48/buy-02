package com.buy01.product_service.security;

import java.util.List;

 
public record AuthenticatedUser(String userId, List<String> roles) {

    public boolean hasRole(String role) {
        return roles != null && roles.stream().anyMatch(r -> r.equalsIgnoreCase(role));
    }
}
