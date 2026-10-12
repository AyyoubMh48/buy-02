package com.buy01.user_service.security;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;

class JwtServiceTest {

    private static final String SECRET = "buy01-super-secret-key-change-this-in-production-please";
    private final JwtService jwtService = new JwtService(SECRET, 3600000L);

    @Test
    void generateToken_andExtractClaims() {
        String token = jwtService.generateToken("user-1", "SELLER");

        assertThat(token).isNotBlank();
        assertThat(jwtService.extractUserId(token)).isEqualTo("user-1");
        assertThat(jwtService.extractRole(token)).isEqualTo("SELLER");
        assertThat(jwtService.isValid(token)).isTrue();
    }

    @Test
    void isValid_rejectsMalformedToken() {
        assertThat(jwtService.isValid("not-a-jwt")).isFalse();
    }

    @Test
    void isValid_rejectsTokenSignedWithOtherKey() {
        JwtService other = new JwtService("another-secret-key-that-is-long-enough-here-1234567890", 3600000L);
        String foreign = other.generateToken("x", "CLIENT");

        assertThat(jwtService.isValid(foreign)).isFalse();
    }

    @Test
    void isValid_rejectsExpiredToken() {
        JwtService expired = new JwtService(SECRET, -1000L);
        String token = expired.generateToken("user-1", "CLIENT");

        assertThat(jwtService.isValid(token)).isFalse();
    }
}