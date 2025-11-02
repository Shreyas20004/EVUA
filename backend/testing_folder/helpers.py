def add_numbers(a, b):
    print "Adding", a, "and", b
    return a + b

def has_key_test(d):
    if d.has_key("x"):
        print "Dictionary has 'x'"
        return True
    else:
        print "No 'x'"
        return False

def byte_string_test():
    s = "plain string"
    u = unicode("unicode string")
    return s, u
