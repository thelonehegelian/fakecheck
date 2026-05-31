import pytest
from src.models.requests import ImageFactCheckRequest
from src.core.exceptions import (
    EmptyContentError,
    ContentTooLargeError,
    ValidationError as FCValidationError
)

def test_image_request_validation_success():
    """Test that a valid image request parses and passes validation successfully."""
    valid_base64 = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    request = ImageFactCheckRequest(image=valid_base64)
    assert request.image == valid_base64
    assert request.priority == "normal"
    assert request.custom_prompt is None

def test_image_request_validation_missing_prefix():
    """Test that an image request without a 'data:image/' prefix is blocked by validation."""
    invalid_base64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    with pytest.raises(FCValidationError) as exc_info:
        ImageFactCheckRequest(image=invalid_base64)
    assert "Must start with 'data:image/' prefix" in str(exc_info.value)

def test_image_request_validation_empty():
    """Test that an empty image request is blocked by validation."""
    with pytest.raises(EmptyContentError) as exc_info:
        ImageFactCheckRequest(image="")
    assert "Image data cannot be empty" in str(exc_info.value)

def test_image_request_validation_too_large():
    """Test that an image request exceeding the size limit is blocked by validation."""
    huge_image_base64 = "data:image/png;base64," + ("A" * 7000005)
    with pytest.raises(ContentTooLargeError) as exc_info:
        ImageFactCheckRequest(image=huge_image_base64)
    assert "too large" in str(exc_info.value)
