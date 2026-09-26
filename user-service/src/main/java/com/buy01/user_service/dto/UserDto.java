package com.buy01.user_service.dto;

import com.buy01.user_service.model.Role;
import lombok.AllArgsConstructor;
import lombok.Data;

@Data
@AllArgsConstructor
public class UserDto {
    private String id;
    private String username;
    private String email;
    private Role role;
    private String avatarUrl;

}