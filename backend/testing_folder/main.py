# -*- coding: utf-8 -*-
print "🚀 Starting complex migration test..."

import sys, os
import helpers
from models.person import Person

# raw_input, unicode, long, and exception syntax
try:
    name = raw_input("Enter your name: ")
    age = long(raw_input("Enter your age: "))
except (ValueError, TypeError), e:
    print "Invalid input:", e
    name, age = u"Guest", 0L

# range / xrange test
for i in xrange(3):
    print "Loop:", i

# exec, eval, and nested scopes
config_code = """
def greet(person):
    print 'Dynamic greet for', person
"""
exec config_code
greet(name)

# lambda and map / filter
nums = range(10)
even = filter(lambda x: x % 2 == 0, nums)
squares = map(lambda x: x ** 2, even)
print "Even squares:", squares

# dictionary and iteritems
data = {"x": 1, "y": 2, "z": 3}
for k, v in data.iteritems():
    print "Pair:", k, v

# old string formatting and unicode
msg = u"Hello %s, you are %d years old" % (name, age)
print msg

# file handling and exception
try:
    f = open("sample.txt", "w")
    f.write("This is a test\n")
    f.close()
except IOError, e:
    print "File error:", e

# Using helper and model
p = Person(name, age)
print "Created person:", p
p.greet()

# list comprehension, tuple unpack, etc.
pairs = [(i, i ** 2) for i in xrange(5)]
for a, b in pairs:
    print "Pair:", a, b

# long integer ops and comparison
big = 12345678901234567890L
if big > age:
    print "Big number is larger"

# execfile and eval test
try:
    execfile("extra_script.py")
except Exception, e:
    print "No extra script:", e

# custom helper calls
print "Sum:", helpers.add_numbers(5, 15)
print "Has key test:", helpers.has_key_test(data)

# unicode and byte string test
s, u = helpers.byte_string_test()
print "String types:", type(s), type(u)

# generator test from model
for val in p.generator_test():
    print "Generated:", val

print "✅ Complex migration test complete."
