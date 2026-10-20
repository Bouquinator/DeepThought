NAME	= mini_echo
CFLAGS	= -Wall -Wextra -Werror

all: $(NAME)

$(NAME): mini_echo.c
	cc $(CFLAGS) mini_echo.c -o $(NAME)

clean:

fclean: clean
	rm -f $(NAME)

re: fclean all

.PHONY: all clean fclean re
