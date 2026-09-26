package com.buy_01.media.repository;

import java.util.List;

import org.springframework.data.mongodb.repository.MongoRepository;
import org.springframework.stereotype.Repository;

import com.buy_01.media.model.entity.MediaMetaData;

@Repository
public interface MediaMetaDataRepository extends MongoRepository<MediaMetaData, String>{
    List<MediaMetaData> findByUploaderId(String uploaderId);    
}