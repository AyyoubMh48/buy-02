package com.buy_01.media.model.dto;

import lombok.Builder;
import lombok.Data;

@Data
@Builder                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           
public class MediaRespDto {
    private String id;
    private String filename;
    private String contentType;
    private String url;
    private long size; 
    private String uploaderId;  
}