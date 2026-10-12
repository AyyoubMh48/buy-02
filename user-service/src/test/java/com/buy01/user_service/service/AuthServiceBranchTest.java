package com.buy01.user_service.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.security.crypto.password.PasswordEncoder;

import com.buy01.user_service.dto.RegisterDto;
import com.buy01.user_service.model.Role;
import com.buy01.user_service.model.User;
import com.buy01.user_service.repository.UserRepository;
import com.buy01.user_service.security.JwtService;

@ExtendWith(MockitoExtension.class)
class AuthServiceBranchTest {

    @Mock
    private UserRepository userRepository;

    @Mock
    private PasswordEncoder passwordEncoder;

    @Mock
    private JwtService jwtService;

    @InjectMocks
    private AuthService authService;

    @BeforeEach
    void setUp() {
        when(passwordEncoder.encode(any())).thenReturn("encoded");
    }

    @Test
    void register_withAvatar_setsAvatar() {
        RegisterDto request = new RegisterDto();
        request.setUsername("bob");
        request.setEmail("  Bob@Example.com ");
        request.setPassword("secret123");
        request.setRole(Role.SELLER);
        request.setAvatarUrl("https://cdn/x.png");
        when(userRepository.existsByEmail("bob@example.com")).thenReturn(false);
        when(userRepository.save(any(User.class))).thenAnswer(inv -> {
            User u = inv.getArgument(0);
            u.setId("u1");
            return u;
        });

        var dto = authService.register(request);

        assertThat(dto.getId()).isEqualTo("u1");
        assertThat(dto.getEmail()).isEqualTo("bob@example.com");
        assertThat(dto.getAvatarUrl()).isEqualTo("https://cdn/x.png");
    }

    @Test
    void register_withNullUsername_storesNull() {
        RegisterDto request = new RegisterDto();
        request.setEmail("c@example.com");
        request.setPassword("secret123");
        request.setRole(Role.CLIENT);
        when(userRepository.existsByEmail("c@example.com")).thenReturn(false);
        when(userRepository.save(any(User.class))).thenAnswer(inv -> {
            User u = inv.getArgument(0);
            u.setId("u2");
            return u;
        });

        var dto = authService.register(request);

        assertThat(dto.getUsername()).isNull();
    }

    @Test
    void register_withBlankAvatar_leavesNull() {
        RegisterDto request = new RegisterDto();
        request.setUsername("dan");
        request.setEmail("d@example.com");
        request.setPassword("secret123");
        request.setRole(Role.CLIENT);
        request.setAvatarUrl("   ");
        when(userRepository.existsByEmail("d@example.com")).thenReturn(false);
        when(userRepository.save(any(User.class))).thenAnswer(inv -> {
            User u = inv.getArgument(0);
            u.setId("u3");
            return u;
        });

        var dto = authService.register(request);

        assertThat(dto.getAvatarUrl()).isNull();
    }
}