package com.buy01.user_service.service;

import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;

import com.buy01.user_service.dto.LoginDto;
import com.buy01.user_service.dto.LoginResponse;
import com.buy01.user_service.dto.RegisterDto;
import com.buy01.user_service.dto.UserDto;
import com.buy01.user_service.exception.EmailAlreadyExistsException;
import com.buy01.user_service.exception.InvalidCredentialsException;
import com.buy01.user_service.model.User;
import com.buy01.user_service.repository.UserRepository;
import com.buy01.user_service.security.JwtService;

@Service
public class AuthService {

    private final UserRepository userRepository;
    private final PasswordEncoder passwordEncoder;
    private final JwtService jwtService;

    public AuthService(
            UserRepository userRepository,
            PasswordEncoder passwordEncoder,
            JwtService jwtService
    ) {
        this.userRepository = userRepository;
        this.passwordEncoder = passwordEncoder;
        this.jwtService = jwtService;
    }

    public UserDto register(RegisterDto request) {

                String email = normalizeEmail(request.getEmail());

                if (userRepository.existsByEmail(email)) {
            throw new EmailAlreadyExistsException(
                    "Email already exists"
            );
        }

        User user = new User();
        String username = request.getUsername() != null ? request.getUsername().trim() : null;
        user.setUsername(username);
        user.setEmail(email);
        user.setPassword(
                passwordEncoder.encode(request.getPassword())
        );
        user.setRole(request.getRole());
        if (request.getAvatarUrl() != null && !request.getAvatarUrl().isBlank()) {
            user.setAvatarUrl(request.getAvatarUrl().trim());
        }

        User savedUser = userRepository.save(user);

        return new UserDto(
                savedUser.getId(),
                savedUser.getUsername(),
                savedUser.getEmail(),
                savedUser.getRole(),
                savedUser.getAvatarUrl()
        );
    }

    public LoginResponse login(LoginDto request) {

                User user = userRepository.findByEmail(normalizeEmail(request.getEmail()))
                .orElseThrow(() ->
                        new InvalidCredentialsException(
                                "Invalid email or password"
                        )
                );

        if (!passwordEncoder.matches(
                request.getPassword(),
                user.getPassword()
        )) {
            throw new InvalidCredentialsException(
                    "Invalid email or password"
            );
        }

        String token = jwtService.generateToken(
                user.getId(),
                user.getRole().name()
        );

        UserDto userDto = new UserDto(
                user.getId(),
                user.getUsername(),
                user.getEmail(),
                user.getRole(),
                user.getAvatarUrl()
        );

        return new LoginResponse(token, userDto);
    }

        private String normalizeEmail(String email) {
                return email.trim().toLowerCase();
        }
}