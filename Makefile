# Credit: This Makefile referes to jserv's template
#         https://github.com/sysprog21
.PHONY: all check clean
TARGET = junk-messenger
GIT_HOOKS := .git/hooks/applied
all: $(GIT_HOOKS) $(TARGET)

$(GIT_HOOKS):
	# @scripts/install-git-hooks
	@echo

include common.mk

CXXFLAGS = -I./src
CXXFLAGS += -O2
CXXFLAGS += -std=gnu99 -Wall -W
CXXFLAGS += -DUNUSED="__attribute__((unused))"
CXXFLAGS += -DNDEBUG
LDFLAGS =

# standard build rules
%.o: %.cpp
	$(VECHO) "  CXX\t$@\n"
	$(Q)$(CXX) -o $@ $(CXXFLAGS) -c -MMD -MF $@.d $<

OBJS = \
    src/main.o
deps += $(OBJS:%.o=%.o.d)

$(TARGET): $(OBJS)
	$(VECHO) "  LD\t$@\n"
	$(Q)$(CC) -o $@ $^ $(LDFLAGS)

check: all
	@scripts/test.sh

clean:
	$(VECHO) "  Cleaning...\n"
	$(Q)$(RM) $(TARGET) $(OBJS) $(deps)

-include $(deps)

