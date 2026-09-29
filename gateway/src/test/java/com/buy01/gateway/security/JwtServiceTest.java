package com.buy01.gateway.security;

import io.jsonwebtoken.Claims;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Keys;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import javax.crypto.SecretKey;
import java.nio.charset.StandardCharsets;
import java.util.Date;

import static org.assertj.core.api.Assertions.assertThat;

class JwtServiceTest {

    private static final String SECRET = "my-ultra-secret-test-key-which-is-at-least-256-bits-long-1234567890";
    private JwtService jwtService;

    @BeforeEach
    void setUp() {
        jwtService = new JwtService(SECRET);
    }

    @Test
    void extractClaims_ValidToken_ReturnsCorrectClaims() {
        SecretKey key = Keys.hmacShaKeyFor(SECRET.getBytes(StandardCharsets.UTF_8));
        String token = Jwts.builder()
                .subject("user-999")
                .claim("role", "SELLER")
                .expiration(new Date(System.currentTimeMillis() + 3600000))
                .signWith(key)
                .compact();

        Claims claims = jwtService.extractClaims(token);

        assertThat(claims.getSubject()).isEqualTo("user-999");
        assertThat(claims.get("role", String.class)).isEqualTo("SELLER");
    }

    @Test
    void isValid_ValidToken_ReturnsTrue() {
        SecretKey key = Keys.hmacShaKeyFor(SECRET.getBytes(StandardCharsets.UTF_8));
        String token = Jwts.builder()
                .subject("user-999")
                .claim("role", "CLIENT")
                .expiration(new Date(System.currentTimeMillis() + 3600000))
                .signWith(key)
                .compact();

        assertThat(jwtService.isValid(token)).isTrue();
    }

    @Test
    void isValid_InvalidOrTamperedToken_ReturnsFalse() {
        assertThat(jwtService.isValid("invalid.token.structure")).isFalse();
        assertThat(jwtService.isValid(null)).isFalse();
        assertThat(jwtService.isValid("")).isFalse();
    }
}
