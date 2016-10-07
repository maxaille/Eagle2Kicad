'''
Created on Apr 5, 2012

@author: Dan
'''
from Common.Shapes import *
import logging
import copy

class DevicePart(object):
    def __init__(self, device, symbolsDict, prefix, gates, converter):
        self.device = device
        self.name = str(device.fullName)
        self.prefix = prefix if prefix else "U"
        self.symbols = [Symbol(symbolsDict[gate.symbol], converter, device, (gate.x, gate.y)) \
                        for gate in gates]
        self.units = 0 #TODO: we have to deal somehow with multiunit devices
        self.textRef = {"x":0, "y":0, "size":0}
        self.textValue = {"x":0, "y":0, "size":0}

        texts = symbolsDict[gates[0].symbol].findall("text")
        for text in texts:
            t = Text(text, converter, True)
            if t.val.upper() == ">NAME":
                self.textRef = {
                    "x": t.x,
                    "y": t.y,
                    "size": t.size,
                    "hJust": t.hJust[0].capitalize(),
                    "vJust": t.vJust[0].capitalize()
                }
            elif t.val.upper() == ">VALUE":
                self.textValue = {
                    "x": t.x,
                    "y": t.y,
                    "size": t.size,
                    "hJust": t.hJust[0].capitalize(),
                    "vJust": t.vJust[0].capitalize()
                }


        for gate in gates:
            if gate.name == "P" or gate.symbol == "PWRN":
                continue
            self.units += 1

    def write(self, symFile):

        """
        DEF name reference unused text_offset draw_pinnumber draw_pinname unit_count units_locked option_flag
        ALIAS name1 name2...
        fields list
        DRAW
            list graphic elements and pins
        ENDDRAW
        ENDDEF
        """
        logging.debug("Writing Device "+self.device.fullName)
        self.isPower = "N" #just keep it normal it's mostly actual

        if self.isPower == "Y":
            token = "#"
        else:
            token = ""

        symFile.write("#Generated for %s package %s\n" % (self.device.fullName, str(self.device.package)) )
        symFile.write("DEF %s %s 0 100 Y Y %d 0 %s\n" % (self.name, self.prefix, self.units, self.isPower) )
        symFile.write("F0 \"%s\" %s %s %s H V %s %sNN\n" % \
            (
                token + self.prefix,
                self.textRef["x"],
                self.textRef["y"],
                self.textRef["size"],
                self.textRef["hJust"],
                self.textRef["vJust"]
            )
        )

        symFile.write("F1 \"%s\" %s %s %s H V %s %sNN\n" % \
            (
                self.name,
                self.textValue["x"],
                self.textValue["y"],
                self.textValue["size"],
                self.textValue["hJust"],
                self.textValue["vJust"]
            )
        )

        if self.device.package is not None:
            symFile.write("$FPLIST\n")
            symFile.write(" " + self.device.package + "\n")
            symFile.write("$ENDFPLIST\n")
        symFile.write("DRAW\n")

        for symbol in self.symbols:
            symbol.write(symFile)

        symFile.write("ENDDRAW\n")
        symFile.write("ENDDEF\n")

class Symbol(object):
    __slots__ = ("name", "isPower", "polygons", "wires", "texts", "pins", "circles", "rectangles", "package", "device")
    #TODO multigate Parts each shape has a unit associated with it...
    #this coresponds to the swap level in the deviceset.
    def __init__(self, node, converter, device=None, offset=None):
        self.polygons = []
        self.wires = []
        self.texts = []
        self.pins = []
        self.circles = []
        self.rectangles = []
        self.name = node.get("name")

        for polygon in node.findall("polygon"):
            self.polygons.append(Polyline(polygon, converter, True, offset))
        for wire in node.findall("wire"):
            self.wires.append(Line(wire, converter, True, offset))
        for text in node.findall("text"):
            if text.text.upper() != ">NAME" and text.text.upper() != ">VALUE":
                self.texts.append(Text(text, converter, True, offset))
        for pin in node.findall("pin"):
            self.pins.append(Pin(pin, converter, True, offset))
        for circle in node.findall("circle"):
            self.circles.append(Circle(circle, converter, True, offset))
        for rectangle in node.findall("rectangle"):
            self.rectangles.append(Rectangle(rectangle, converter, True))

        if device:
            for pin in self.pins[:]: #number all pins
                pads = device.getPadsByPinName(pin.name)
                pin.pad = pads[0]
                for pad in pads[1:]:
                    newpin = copy.copy(pin)
                    newpin.pad = pad
                    newpin.shape = "N" + newpin.shape
                    self.pins.append(newpin)

        self.isPower = "P"
        for pin in self.pins:
            if pin.direction != "w":
                self.isPower = "N"
                break


    def write(self, symFile):
        """
        DEF name reference unused text_offset draw_pinnumber draw_pinname unit_count units_locked option_flag
        ALIAS name1 name2...
        fields list
        DRAW
            list graphic elements and pins
        ENDDRAW
        ENDDEF
        """
        logging.debug("Writing Symbol "+self.name)
        for polygon in self.polygons:
            symFile.write(polygon.symRep())
        for wire in self.wires:
            symFile.write(wire.symRep())
        for text in self.texts:
            symFile.write(text.symRep())
        for pin in self.pins:
            symFile.write(pin.symRep())
        for circle in self.circles:
            symFile.write(circle.symRep())
        for rectangle in self.rectangles:
            symFile.write(rectangle.symRep())


class Pin(object):
#          name          %String;       #REQUIRED
#          x             %Coord;        #REQUIRED
#          y             %Coord;        #REQUIRED
#          visible       %PinVisible;   "both"
#          length        %PinLength;    "long"
#          direction     %PinDirection; "io"
#          function      %PinFunction;  "none"
#          swaplevel     %Int;          "0"
#          rot           %Rotation;     "R0"
    __slots__ = ("name",
                 "direction",
                 "rotation",
                 "shape", "length",
                 "numSize", "nameSize",
                 "x", "y", "pad")

    def __init__(self, node, converter, noTranspose=True, offset=None):
        self.name = node.get("name")
        if self.name[0] == "!":
            self.name = "~" + self.name[1:]
        x, y = converter.convertCoordinate(node.get("x"), node.get("y"), True, True)
        if offset != None:
            dX, dY = converter.convertCoordinate(offset[0], offset[1], noTranspose)
            x += dX
            y += dY

        self.x = str(x)
        self.y = str(y)

        self.getShape(node, converter)
        self.getDirection(node)
        self.getVisibility(node)
        self.pad = self.name

    def getShape(self, node, converter):
        #<!ENTITY % PinLength         "(point | short | middle | long)">
        length = node.get("length")
        if length == "middle":
            self.length = "200"
        elif length == "short":
            self.length = "100"
        elif length == "point":
            self.length = "0"
        else:
            self.length = "300" #defaults to long

        #<!ENTITY % PinFunction       "(none | dot | clk | dotclk)">
        func = node.get("function")
        if func == "dot":
            self.shape = "I"
        elif func == "clk":
            self.shape = "C"
        elif func == "dotclk":
            self.shape = "CI"
        else:
            self.shape = ""#defualts to line

        #on = U (up) D (down) R (right) L (left).

        rot = converter.convertRotation(node.get("rot"))['rot']
        if rot == 0:
            self.rotation = "R"
        elif rot == 900:
            self.rotation = "U"
        elif rot == 1800:
            self.rotation = "L"
        elif rot == 2700:
            self.rotation = "D"
        else:
            print("Warning: symbol pin not at 90 degrees\n" + self.name + ": " + str(rot))

    def getDirection(self, node):
        #<!ENTITY % PinDirection "(nc | in | out | io | oc | pwr | pas | hiz | sup)">
        myDict = {"nc": "N", #not connected
                  "in": "I", #input
                  "out": "O", #output
                  "io": "B", #bidirectional
                  "oc": "C", #open Collector
                  "pwr": "W", #power input
                  "pas": "P", #Passive
                  "hiz": "U", #unspecified TODO this might be open emitter (E)
                  "sup": "w"   #power output
        }
        direction = myDict.get(node.get("direction"))
        if direction == None:
            direction = "B" #default to bidi
        self.direction = direction

    def getVisibility(self, node):
        #<!ENTITY % PinVisible        "(off | pad | pin | both)">
        vis = node.get("visible")

        self.numSize = "50"
        self.nameSize = "0"

        if vis != "off" and vis != "pad":
            self.nameSize = "60"

    def symRep(self):
        num = self.pad
        if len(num) > 4:
            num = num[:4]
        myString = "X " + self.name + " " + num + " " + self.x + " " + self.y + " " + self.length
        myString += " " + self.rotation + " " + self.numSize + " " + self.nameSize + " 0 0 "
        myString += self.direction + " " + self.shape + "\n"
        return myString
