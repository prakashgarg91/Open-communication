"""Mathematical utility functions module.

This module provides common mathematical functions including Fibonacci sequence,
prime number checking, greatest common divisor calculation, and factorial computation.
"""


def fibonacci(n: int) -> int:
    """Calculate the nth Fibonacci number.
    
    The Fibonacci sequence is defined as:
    - F(0) = 0
    - F(1) = 1
    - F(n) = F(n-1) + F(n-2) for n > 1
    
    Args:
        n: The position in the Fibonacci sequence (must be non-negative).
    
    Returns:
        The nth Fibonacci number.
    
    Raises:
        ValueError: If n is negative.
    """
    if n < 0:
        raise ValueError("n must be a non-negative integer")
    if n == 0:
        return 0
    if n == 1:
        return 1
    
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b


def is_prime(n: int) -> bool:
    """Check if a number is prime.
    
    A prime number is a natural number greater than 1 that has no positive
    divisors other than 1 and itself.
    
    Args:
        n: The number to check.
    
    Returns:
        True if n is prime, False otherwise.
    """
    if n < 2:
        return False
    if n == 2:
        return True
    if n % 2 == 0:
        return False
    
    # Check odd divisors up to square root of n
    for i in range(3, int(n ** 0.5) + 1, 2):
        if n % i == 0:
            return False
    return True


def gcd(a: int, b: int) -> int:
    """Calculate the greatest common divisor using the Euclidean algorithm.
    
    The Euclidean algorithm repeatedly replaces the larger number by its remainder
    when divided by the smaller number until one of the numbers becomes zero.
    The non-zero number is then the GCD.
    
    Args:
        a: First integer.
        b: Second integer.
    
    Returns:
        The greatest common divisor of a and b (always non-negative).
    """
    a, b = abs(a), abs(b)
    while b:
        a, b = b, a % b
    return a


def factorial(n: int) -> int:
    """Calculate the factorial of a non-negative integer.
    
    The factorial of n (written as n!) is the product of all positive integers
    less than or equal to n.
    
    Args:
        n: A non-negative integer.
    
    Returns:
        The factorial of n.
    
    Raises:
        ValueError: If n is negative.
    """
    if n < 0:
        raise ValueError("factorial() not defined for negative values")
    
    result = 1
    for i in range(2, n + 1):
        result *= i
    return result
