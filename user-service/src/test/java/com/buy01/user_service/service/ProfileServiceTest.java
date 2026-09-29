package com.buy01.user_service.service;

import com.buy01.user_service.client.MediaServiceClient;
import com.buy01.user_service.dto.UserDto;
import com.buy01.user_service.exception.UserNotFoundException;
import com.buy01.user_service.model.Role;
import com.buy01.user_service.model.User;
import com.buy01.user_service.repository.UserRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class ProfileServiceTest {

    @Mock
    private UserRepository userRepository;

    @Mock
    private MediaServiceClient mediaServiceClient;

    @InjectMocks
    private ProfileService profileService;

    private User sampleUser;

    @BeforeEach
    void setUp() {
        sampleUser = new User();
        sampleUser.setId("user-1");
        sampleUser.setUsername("alice");
        sampleUser.setEmail("alice@example.com");
        sampleUser.setRole(Role.CLIENT);
        sampleUser.setAvatarUrl("https://cdn.example.com/avatar.png");
    }

    @Test
    void getProfile_UserExists_ReturnsUserDto() {
        when(userRepository.findById("user-1")).thenReturn(Optional.of(sampleUser));

        UserDto dto = profileService.getProfile("user-1");

        assertThat(dto).isNotNull();
        assertThat(dto.getId()).isEqualTo("user-1");
        assertThat(dto.getUsername()).isEqualTo("alice");
        assertThat(dto.getEmail()).isEqualTo("alice@example.com");
    }

    @Test
    void getProfile_UserNotFound_ThrowsException() {
        when(userRepository.findById("unknown")).thenReturn(Optional.empty());

        assertThrows(UserNotFoundException.class, () -> profileService.getProfile("unknown"));
    }

    @Test
    void updateProfile_UpdatesUsernameAndPersists() {
        when(userRepository.findById("user-1")).thenReturn(Optional.of(sampleUser));
        when(userRepository.save(any(User.class))).thenAnswer(inv -> inv.getArgument(0));

        UserDto updated = profileService.updateProfile("user-1", "alice_new", null);

        assertThat(updated.getUsername()).isEqualTo("alice_new");
        verify(userRepository).save(any(User.class));
    }
}
