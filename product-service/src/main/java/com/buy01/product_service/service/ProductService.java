package com.buy01.product_service.service;

import java.time.Instant;
import java.util.List;

import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.stereotype.Service;

import com.buy01.product_service.client.MediaServiceClient;
import com.buy01.product_service.dtos.external.MediaMetadataResponse;
import com.buy01.product_service.dtos.req.CreateProductRequest;
import com.buy01.product_service.dtos.req.LinkImagesRequest;
import com.buy01.product_service.dtos.req.UpdateProduct;
import com.buy01.product_service.dtos.response.ProductResponse;
import com.buy01.product_service.events.ProductCreatedEvent;
import com.buy01.product_service.exceptionsHandler.BadRequest;
import com.buy01.product_service.exceptionsHandler.ResourceNotFoundException;
import com.buy01.product_service.exceptionsHandler.UnauthorizedException;
import com.buy01.product_service.models.Product;
import com.buy01.product_service.repository.ProductRepository;
import com.buy01.product_service.security.AuthenticatedUser;

import lombok.RequiredArgsConstructor;

@Service
@RequiredArgsConstructor
 
public class ProductService {
 
 private static final String SELLER_ROLE = "SELLER";
 private final ProductRepository productRepository;
 private final MediaServiceClient mediaServiceClient;
 private final KafkaTemplate<String, ProductCreatedEvent> kafkaTemplate;
//   this is going to bring all the products :;


 public  List<ProductResponse> getThemAll(){
    return productRepository.findAll().stream().map(this::toResponse).toList();
 } 
 


 public Product findAproduuct(String id){
    return productRepository.findById(id).orElseThrow( ( ) -> 
    new ResourceNotFoundException("sorrry man no product found with this id: " + id));
 }

public ProductResponse getOneProduct(String is){
    return toResponse(findAproduuct(is));
}

public Product findMyProduct(String id , AuthenticatedUser user){
    Product p = findAproduuct(id);
    if(!p.getOwnerId().equals(user.userId())){
        throw new UnauthorizedException("u are not the owner of this product");
    }
    return p;
}

public List<ProductResponse> myProducts(AuthenticatedUser user){
    return productRepository.findByOwnerId(user.userId()).stream().map(this::toResponse).toList();
}


public void isSeller(AuthenticatedUser user){
    if (!user.hasRole(SELLER_ROLE)) {
        throw new UnauthorizedException("u need to be a seller to add a new product");
    }
}


//  i dn't know if this the right approach to it or not 
// firstt we gonnna create the product without media , therefore we gonna wait for a basic product response
// then will wiat for l media to be created triger the media service via REST then update the product images field . 
//  fach adi nabghiw n requesteewhom me l frontend , we gonna send the prodct with is image URLs , so we gonna fetch them directly frome cloudinary;

// yla bantkum shi haja hassan ndirouhah 🤓

public ProductResponse linkImages(String is , LinkImagesRequest req , AuthenticatedUser u){
    isSeller(u);
    Product p = findMyProduct(is, u);
    List<String> resolvedlinks = req.imageUrls().stream().
    map(m -> resolvedMediaUrl(m, u)).toList();
    p.setImages(resolvedlinks.toArray(new String[0]));
    p.setMediaIds(req.imageUrls().toArray(new String[0]));
    p.setUpdatedAt(Instant.now());
    return toResponse(productRepository.save(p));
}


private String resolvedMediaUrl(String mediaId, AuthenticatedUser user) {
        MediaMetadataResponse media = mediaServiceClient.fetchMetadata(mediaId);
        if (!user.userId().equals(media.uploaderId())) {
            throw new UnauthorizedException("You do not own media: " + mediaId);
        }
        return media.url();
}


public ProductResponse newProduct(CreateProductRequest req , AuthenticatedUser user){
        isSeller(user);
    requireImages(req.mediaIds());
        Instant now = Instant.now();

        List<String> resolvedImages = (req.mediaIds() != null && !req.mediaIds().isEmpty())
                ? req.mediaIds().stream().map(m -> resolvedMediaUrl(m, user)).toList()
                : List.of();

        Product p = Product.builder()
                .name(req.name())
                .description(req.description())
                .price(req.price())
                .quantity(req.quantity())
                .ownerId(user.userId())
                .images(resolvedImages.toArray(new String[0]))
                .mediaIds(req.mediaIds().toArray(new String[0]))
                .createdAt(now)
                .updatedAt(now)
                .build();
        Product saved = productRepository.save(p);
        kafkaTemplate.send(
            "PRODUCT_CREATED",
            saved.getId(),
            new ProductCreatedEvent(
                saved.getId(),
                saved.getOwnerId(),
                saved.getName(),
                saved.getPrice(),
                saved.getQuantity(),
                saved.getCreatedAt()
            )
        );
        return toResponse(saved);
    }


public ProductResponse updateProduct(String id, UpdateProduct request, AuthenticatedUser user) {
    requireImages(request.mediaIds());
    List<String> resolvedImages = (request.mediaIds() != null && !request.mediaIds().isEmpty())
                ? request.mediaIds().stream().map(m -> resolvedMediaUrl(m, user)).toList()
                : List.of();

        isSeller(user);
        Product product = findMyProduct(id, user);

        product.setName(request.name());
        product.setDescription(request.description());
        product.setPrice(request.price());
        product.setImages(resolvedImages.toArray(new String[0]));
        product.setMediaIds(request.mediaIds().toArray(new String[0]));
        product.setQuantity(request.quantity());
        product.setUpdatedAt(Instant.now());

        return toResponse(productRepository.save(product));
    }

    private void requireImages(List<String> mediaIds) {
        if (mediaIds == null || mediaIds.isEmpty()) {
            throw new BadRequest("At least one product image is required");
        }
    }



public void deleteP(String id , AuthenticatedUser user){
    isSeller(user);
   Product p = findMyProduct(id, user);
    productRepository.delete(p);
}
 
  private ProductResponse toResponse(Product product) {
        return new ProductResponse(
                product.getId(),
                product.getName(),
                product.getDescription(),
                product.getPrice(),
                product.getOwnerId(),
                product.getImages(),
                product.getMediaIds(),
                product.getQuantity());
    }
 
}