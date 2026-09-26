package com.buy_01.media.model.entity;

import java.time.LocalDateTime;

import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.mapping.Document;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@Document(collection = "media_metadata")
public class MediaMetaData {
    @Id
    private String id;
    private String filename;
    private String originalFilename;
    private String contentType;
    private long size;
    private String storagePath;
    private String uploaderId;
    private LocalDateTime uploadedAt;
    
}
