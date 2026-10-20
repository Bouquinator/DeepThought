NAME	= libft.a
CC		= cc
CFLAGS	= -Wall -Wextra -Werror
SRCS	= part1.c part2.c
BSRCS	= bonus.c
OBJS	= $(SRCS:.c=.o)
BOBJS	= $(BSRCS:.c=.o)

all: $(NAME)

$(NAME): $(OBJS)
	ar rcs $(NAME) $(OBJS)

bonus: .bonus

.bonus: $(NAME) $(BOBJS)
	ar rcs $(NAME) $(BOBJS)
	@touch .bonus

%.o: %.c libft.h
	$(CC) $(CFLAGS) -c $< -o $@

clean:
	rm -f $(OBJS) $(BOBJS) .bonus

fclean: clean
	rm -f $(NAME)

re: fclean all

.PHONY: all clean fclean re bonus
