def factorial(n):
    """
    Calculates the factorial of a non-negative integer using iteration.

    Args:
        n (int): The non-negative integer for which to calculate the factorial.

    Returns:
        int: The factorial of n.

    Raises:
        ValueError: If n is a negative number.
    """
    if not isinstance(n, int):
        raise TypeError("Input must be an integer.")
    if n < 0:
        raise ValueError("Factorial is not defined for negative numbers.")
    
    result = 1
    for i in range(1, n + 1):
        result *= i
    return result

if __name__ == "__main__":
    # Test cases
    print(f"Factorial of 0: {factorial(0)}")    # Expected: 1
    print(f"Factorial of 1: {factorial(1)}")    # Expected: 1
    print(f"Factorial of 5: {factorial(5)}")    # Expected: 120
    print(f"Factorial of 10: {factorial(10)}")  # Expected: 3628800

    # Test with negative number (should raise ValueError)
    try:
        print(f"Factorial of -3: {factorial(-3)}")
    except ValueError as e:
        print(f"Error: {e}")

    # Test with non-integer (should raise TypeError)
    try:
        print(f"Factorial of 3.5: {factorial(3.5)}")
    except TypeError as e:
        print(f"Error: {e}")
