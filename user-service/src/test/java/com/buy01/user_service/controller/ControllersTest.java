package com.buy01.user_service.controller;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.when;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.http.HttpStatus;

import com.buy01.user_service.dto.LoginDto;
import com.buy01.user_service.dto.LoginResponse;
import com.buy01.user_service.dto.RegisterDto;
import com.buy01.user_service.dto.UpdateProfileRequest;
import com.buy01.user_service.dto.UserDto;
import com.buy01.user_service.model.Role;
import com.buy01.user_service.service.AuthService;
import com.buy01.user_service.service.ProfileService;

@ExtendWith(MockitoExtension.class)
class ControllersTest {

    @Mock
    private AuthService authService;

    @Mock
    private ProfileService profileService;

    @InjectMocks
    private AuthController authController;

    @InjectMocks
    private ProfileController profileController;

    private final UserDto userDto = new UserDto("u1", "alice", "a@b.com", Role.CLIENT, null);
    private final LoginResponse loginResponse = new LoginResponse("token", userDto);

    @Test
    void register_returnsCreated() {
        RegisterDto request = new RegisterDto();
        request.setEmail("a@b.com");
        request.setPassword("secret123");
        request.setRole(Role.CLIENT);
        when(authService.register(request)).thenReturn(userDto);
        when(authService.login(org.mockito.ArgumentMatchers.any(LoginDto.class))).thenReturn(loginResponse);

        var response = authController.register(request);

        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.CREATED);
        assertThat(response.getBody().getToken()).isEqualTo("token");
    }

    @Test
    void login_returnsOk() {
        LoginDto request = new LoginDto();
        when(authService.login(request)).thenReturn(loginResponse);

        assertThat(authController.login(request).getStatusCode()).isEqualTo(HttpStatus.OK);
    }

    @Test
    void getMe_returnsProfile() {
        when(profileService.getProfile("u1")).thenReturn(userDto);

        assertThat(profileController.getMe("u1").getUsername()).isEqualTo("alice");
    }

    @Test
    void updateMe_returnsProfile() {
        UpdateProfileRequest request = new UpdateProfileRequest("alice", null);
        when(profileService.updateProfile("u1", "alice", null)).thenReturn(userDto);

        assertThat(profileController.updateMe("u1", request)).isSameAs(userDto);
    }
}