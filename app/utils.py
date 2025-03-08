import phonenumbers
from typing import Optional

def normalize_phone_number(phone: str) -> str:
    """
    Normalize a phone number to E.164 format.
    
    Args:
        phone: The phone number to normalize
        
    Returns:
        The normalized phone number in E.164 format
        
    Raises:
        ValueError: If the phone number cannot be parsed or is invalid
    """
    try:
        # Clean up the phone number
        phone = phone.strip().replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
        
        # Parse and validate the phone number
        parsed_number = phonenumbers.parse(phone, "KZ")
        if not phonenumbers.is_valid_number(parsed_number):
            raise ValueError('Invalid phone number format')
        
        # Return E164 format for consistency
        return phonenumbers.format_number(parsed_number, phonenumbers.PhoneNumberFormat.E164)
    except Exception as e:
        raise ValueError(f'Invalid phone number: {e}')

def format_phone_for_display(phone: str) -> str:
    """
    Format a phone number for display in international format.
    
    Args:
        phone: The phone number to format
        
    Returns:
        The formatted phone number for display
    """
    try:
        parsed_number = phonenumbers.parse(phone)
        return phonenumbers.format_number(parsed_number, phonenumbers.PhoneNumberFormat.INTERNATIONAL)
    except Exception:
        return phone  # Return the original if parsing fails

def is_valid_phone_number(phone: str) -> bool:
    """
    Check if a phone number is valid.
    
    Args:
        phone: The phone number to check
        
    Returns:
        True if the phone number is valid, False otherwise
    """
    try:
        # Clean up the phone number
        phone = phone.strip().replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
        parsed_number = phonenumbers.parse(phone)
        return phonenumbers.is_valid_number(parsed_number)
    except Exception:
        return False

def extract_country_code(phone: str) -> Optional[str]:
    """
    Extract the country code from a phone number.
    
    Args:
        phone: The phone number to extract the country code from
        
    Returns:
        The country code as a string with a + prefix, or None if it can't be extracted
    """
    try:
        parsed_number = phonenumbers.parse(phone)
        country_code = parsed_number.country_code
        return f"+{country_code}"
    except Exception:
        return None