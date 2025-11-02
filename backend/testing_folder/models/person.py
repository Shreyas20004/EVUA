class Person:
    def __init__(self, name, age):
        self.name = name
        self.age = age

    def __repr__(self):
        return "Person(name=%s, age=%s)" % (self.name, self.age)

    def greet(self):
        print "Hi,", self.name

    def generator_test(self):
        for i in xrange(2):
            yield i * 2
