package com.buy01.user_service.controller;

import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import com.buy01.user_service.dto.LoginDto;
import com.buy01.user_service.dto.LoginResponse;
import com.buy01.user_service.dto.RegisterDto;
import com.buy01.user_service.dto.UserDto;
import com.buy01.user_service.service.AuthService;

import jakarta.validation.Valid;

@RestController
@RequestMapping("/auth")
public class AuthController {

    private final AuthService authService;

    public AuthController(AuthService authService) {
        this.authService = authService;
    }

    @PostMapping("/register")
    public ResponseEntity<LoginResponse> register(@Valid @RequestBody RegisterDto request) {
        UserDto user = authService.register(request);
        LoginDto loginRequest = new LoginDto();
        loginRequest.setEmail(request.getEmail());
        loginRequest.setPassword(request.getPassword());
        String token = authService.login(loginRequest).getToken();

        return ResponseEntity.status(HttpStatus.CREATED).body(new LoginResponse(token, user));
    }

    @PostMapping("/login")
    public ResponseEntity<LoginResponse> login(
            @Valid @RequestBody LoginDto request
    ) {
        LoginResponse response = authService.login(request);

        return ResponseEntity.ok(response);
    }
}