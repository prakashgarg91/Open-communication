"""Test suite for mathtools module.

This module contains comprehensive pytest tests for all functions in mathtools,
including edge cases and error handling.
"""

import pytest
from mathtools import fibonacci, is_prime, gcd, factorial


class TestFibonacci:
    """Test cases for the fibonacci function."""

    def test_fibonacci_zero(self):
        """Test fibonacci(0) returns 0."""
        assert fibonacci(0) == 0

    def test_fibonacci_one(self):
        """Test fibonacci(1) returns 1."""
        assert fibonacci(1) == 1

    def test_fibonacci_ten(self):
        """Test fibonacci(10) returns 55 (10th Fibonacci number)."""
        assert fibonacci(10) == 55

    def test_fibonacci_negative(self):
        """Test fibonacci with negative input raises ValueError."""
        with pytest.raises(ValueError, match="n must be a non-negative integer"):
            fibonacci(-1)

    def test_fibonacci_negative_five(self):
        """Test fibonacci with -5 raises ValueError."""
        with pytest.raises(ValueError):
            fibonacci(-5)

    def test_fibonacci_sequence(self):
        """Test first few fibonacci numbers for consistency."""
        expected = [0, 1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89]
        for i, expected_value in enumerate(expected):
            assert fibonacci(i) == expected_value


class TestIsPrime:
    """Test cases for the is_prime function."""

    def test_is_prime_small_prime(self):
        """Test is_prime with small prime numbers."""
        assert is_prime(2) is True
        assert is_prime(3) is True
        assert is_prime(5) is True
        assert is_prime(7) is True

    def test_is_prime_large_prime(self):
        """Test is_prime with larger prime numbers."""
        assert is_prime(97) is True
        assert is_prime(101) is True

    def test_is_prime_composite(self):
        """Test is_prime with composite numbers returns False."""
        assert is_prime(4) is False
        assert is_prime(9) is False
        assert is_prime(15) is False
        assert is_prime(100) is False

    def test_is_prime_less_than_two(self):
        """Test is_prime with numbers less than 2 returns False."""
        assert is_prime(0) is False
        assert is_prime(1) is False
        assert is_prime(-1) is False

    def test_is_prime_even_number(self):
        """Test is_prime correctly identifies even composites."""
        assert is_prime(6) is False
        assert is_prime(12) is False
        assert is_prime(50) is False


class TestGcd:
    """Test cases for the gcd function."""

    def test_gcd_standard_case(self):
        """Test gcd with standard positive integers."""
        assert gcd(12, 18) == 6
        assert gcd(48, 18) == 6
        assert gcd(100, 25) == 25

    def test_gcd_with_zero(self):
        """Test gcd when one argument is zero."""
        assert gcd(5, 0) == 5
        assert gcd(0, 5) == 5
        assert gcd(0, 0) == 0

    def test_gcd_both_zeros(self):
        """Test gcd(0, 0) returns 0."""
        assert gcd(0, 0) == 0

    def test_gcd_coprime_numbers(self):
        """Test gcd with coprime numbers returns 1."""
        assert gcd(7, 13) == 1
        assert gcd(17, 23) == 1

    def test_gcd_negative_numbers(self):
        """Test gcd handles negative numbers correctly."""
        assert gcd(-12, 18) == 6
        assert gcd(12, -18) == 6
        assert gcd(-12, -18) == 6


class TestFactorial:
    """Test cases for the factorial function."""

    def test_factorial_zero(self):
        """Test factorial(0) returns 1."""
        assert factorial(0) == 1

    def test_factorial_positive(self):
        """Test factorial with positive integers."""
        assert factorial(1) == 1
        assert factorial(5) == 120
        assert factorial(10) == 3628800

    def test_factorial_negative(self):
        """Test factorial with negative input raises ValueError."""
        with pytest.raises(ValueError, match="factorial\\(\\) not defined for negative values"):
            factorial(-1)

    def test_factorial_negative_five(self):
        """Test factorial(-5) raises ValueError."""
        with pytest.raises(ValueError):
            factorial(-5)

    def test_factorial_sequence(self):
        """Test factorial values for first few numbers."""
        assert factorial(1) == 1
        assert factorial(2) == 2
        assert factorial(3) == 6
        assert factorial(4) == 24
