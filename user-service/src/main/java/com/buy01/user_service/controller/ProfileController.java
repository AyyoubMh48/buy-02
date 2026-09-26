package com.buy01.user_service.controller;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import com.buy01.user_service.dto.UpdateProfileRequest;
import com.buy01.user_service.dto.UserDto;
import com.buy01.user_service.service.ProfileService;

import jakarta.validation.Valid;

@RestController
@RequestMapping("/me")
public class ProfileController {

    private final ProfileService profileService;

    public ProfileController(ProfileService profileService) {
        this.profileService = profileService;
    }

    @GetMapping
    public UserDto getMe(
            @RequestHeader("X-User-Id") String userId
    ) {
        return profileService.getProfile(userId);
    }

    @PutMapping
    public UserDto updateMe(
            @RequestHeader("X-User-Id") String userId,
            @Valid @RequestBody UpdateProfileRequest body
    ) {
        return profileService.updateProfile(
                userId,
                body.username(),
                body.avatarUrl()
        );
    }
}