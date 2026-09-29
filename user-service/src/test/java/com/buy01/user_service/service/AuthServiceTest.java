package com.buy01.user_service.service;

import com.buy01.user_service.dto.LoginDto;
import com.buy01.user_service.dto.LoginResponse;
import com.buy01.user_service.dto.RegisterDto;
import com.buy01.user_service.dto.UserDto;
import com.buy01.user_service.exception.EmailAlreadyExistsException;
import com.buy01.user_service.exception.InvalidCredentialsException;
import com.buy01.user_service.model.Role;
import com.buy01.user_service.model.User;
import com.buy01.user_service.repository.UserRepository;
import com.buy01.user_service.security.JwtService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.security.crypto.password.PasswordEncoder;

import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class AuthServiceTest {

    @Mock
    private UserRepository userRepository;

    @Mock
    private PasswordEncoder passwordEncoder;

    @Mock
    private JwtService jwtService;

    @InjectMocks
    private AuthService authService;

    private User sampleUser;

    @BeforeEach
    void setUp() {
        sampleUser = new User();
        sampleUser.setId("user-123");
        sampleUser.setUsername("johndoe");
        sampleUser.setEmail("john@example.com");
        sampleUser.setPassword("encoded-secret");
        sampleUser.setRole(Role.CLIENT);
    }

    @Test
    void register_Success() {
        RegisterDto request = new RegisterDto();
        request.setUsername("johndoe");
        request.setEmail("john@example.com");
        request.setPassword("password123");
        request.setRole(Role.CLIENT);

        when(userRepository.existsByEmail("john@example.com")).thenReturn(false);
        when(passwordEncoder.encode("password123")).thenReturn("encoded-secret");
        when(userRepository.save(any(User.class))).thenReturn(sampleUser);

        UserDto result = authService.register(request);

        assertThat(result).isNotNull();
        assertThat(result.getId()).isEqualTo("user-123");
        assertThat(result.getEmail()).isEqualTo("john@example.com");
        assertThat(result.getRole()).isEqualTo(Role.CLIENT);
        verify(userRepository).save(any(User.class));
    }

    @Test
    void register_DuplicateEmail_ThrowsException() {
        RegisterDto request = new RegisterDto();
        request.setEmail("john@example.com");
        request.setPassword("password123");
        request.setRole(Role.CLIENT);

        when(userRepository.existsByEmail("john@example.com")).thenReturn(true);

        assertThrows(EmailAlreadyExistsException.class, () -> authService.register(request));
        verify(userRepository, never()).save(any(User.class));
    }

    @Test
    void login_Success() {
        LoginDto request = new LoginDto();
        request.setEmail("john@example.com");
        request.setPassword("password123");

        when(userRepository.findByEmail("john@example.com")).thenReturn(Optional.of(sampleUser));
        when(passwordEncoder.matches("password123", "encoded-secret")).thenReturn(true);
        when(jwtService.generateToken("user-123", "CLIENT")).thenReturn("mocked-jwt-token");

        LoginResponse response = authService.login(request);

        assertThat(response).isNotNull();
        assertThat(response.getToken()).isEqualTo("mocked-jwt-token");
        assertThat(response.getUser().getEmail()).isEqualTo("john@example.com");
    }

    @Test
    void login_WrongPassword_ThrowsInvalidCredentials() {
        LoginDto request = new LoginDto();
        request.setEmail("john@example.com");
        request.setPassword("wrong-password");

        when(userRepository.findByEmail("john@example.com")).thenReturn(Optional.of(sampleUser));
        when(passwordEncoder.matches("wrong-password", "encoded-secret")).thenReturn(false);

        assertThrows(InvalidCredentialsException.class, () -> authService.login(request));
        verify(jwtService, never()).generateToken(any(), any());
    }

    @Test
    void login_UserNotFound_ThrowsInvalidCredentials() {
        LoginDto request = new LoginDto();
        request.setEmail("nonexistent@example.com");
        request.setPassword("password123");

        when(userRepository.findByEmail("nonexistent@example.com")).thenReturn(Optional.empty());

        assertThrows(InvalidCredentialsException.class, () -> authService.login(request));
        verify(passwordEncoder, never()).matches(any(), any());
    }
}
