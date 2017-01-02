#!/usr/bin/env python
# Distributed under the terms of the GNU Lesser General Public License v3.0
### Author: Neon22 - github 2016


###
import inkex, simplestyle
import fret_scale as fs
import os # for scala file filtering
from math import radians, cos, sin, pi


###----------------------------------------------------------------------------
### Styles - color and size settings
Black = "#000000"
Font_height = 5
# factor used for marker radius
marker_rad_factor = 4
Line_style =  { 'stroke'        : Black,
                'stroke-width'  : '0.2px',
                'fill'          : "none"     }
Dash_style =  { 'stroke'           : Black,
                'stroke-width'     : '0.1px',
                'stroke-dasharray' : '0.9,0.9',
                'fill'             : "none" }
Label_style = { 'font-size'     : str(int(Font_height))+'px',
                'font-family'   : 'arial',
                'text-anchor'   : 'end', # middle
                'fill'          : Black }
Centerline_style =   { 'stroke'           : Black,
                       'stroke-width'     : '0.1px',
                       'stroke-dasharray' : '1.2,0.7,0.3,0.7',
                       'fill'             : "none" }


# Helper functions
def build_line( (x1, y1), (x2, y2), unitFactor):
    path = 'M %s,%s L %s,%s' % (x1*unitFactor, y1*unitFactor, x2*unitFactor, y2*unitFactor)
    return path

def build_notch(x,y, notch_width, unitFactor, dir=1):
    """ draw a notch around the x value
        - dir=-1 means notch is on other side
    """
    w_2 = notch_width/2
    x1 = x - w_2
    x2 = x + w_2
    y2 = y + notch_width*dir
    path = 'L %s,%s L %s,%s' % (x1*unitFactor, y*unitFactor, x1*unitFactor, y2*unitFactor)
    path += 'L %s,%s L %s,%s' % (x2*unitFactor, y2*unitFactor, x2*unitFactor, y*unitFactor)
    return path

def draw_center_cross(x,y, parent, length=2, style=Line_style):
    " center cross for holes "
    d = 'M {0},{1} l {2},0 M {3},{4} l 0,{2}'.format(x-length,y, length*2, x,y-length)
    cross_attribs = { inkex.addNS('label','inkscape'): 'Center cross',
                      'style': simplestyle.formatStyle(style), 'd': d }
    inkex.etree.SubElement(parent, inkex.addNS('path','svg'), cross_attribs )

def draw_SVG_circle(cx, cy, radius, parent, name='circle', style=Line_style):
    " structure an SVG circle entity under parent "
    circ_attribs = {'style': simplestyle.formatStyle(style),
                    'cx': str(cx), 'cy': str(cy), 
                    'r': str(radius),
                    inkex.addNS('label','inkscape'): name}
    circle = inkex.etree.SubElement(parent, inkex.addNS('circle','svg'), circ_attribs )

def draw_circle_marker(x,y, radius, parent):
    " circle with cross at center "
    draw_center_cross(x, y, parent, radius/5.0)
    draw_SVG_circle(x, y, radius, parent)


###
class Fret_ruler(inkex.Effect):

    def __init__(self):
        inkex.Effect.__init__(self)
        # main tab
        self.OptionParser.add_option('--method',         action='store', type='string',
                                  dest='method',         default='12th Root of 2', help="Method to calculate scale")
        self.OptionParser.add_option('--draw_style',     action='store', type='string',
                                  dest='draw_style',     default='Ruler', help="How to draw the Ruler/NEck")
        self.OptionParser.add_option("--nth",            action="store", type="int",
                                  dest="nth",            default=12, help="For different number of notes in a scale")
        self.OptionParser.add_option('--scala_filename', action='store', type='string',
                                  dest='scala_filename', default='12tet', help="Name of file in scales directory")
        self.OptionParser.add_option("--units",          action="store", type="string",
                                  dest="units",          default="in", help="The units of entered dimensions")
        self.OptionParser.add_option("--length",         action="store", type="float",
                                  dest="length",         default=25.5, help="Length of the Scale (and Ruler)")
        self.OptionParser.add_option("--width",          action="store", type="float",
                                  dest="width",          default=1.5, help="Width of the Ruler (= Nut if drawing a neck)")
        self.OptionParser.add_option("--frets",          action="store", type="int",
                                  dest="frets",          default=18, help="number of frets on the scale")
        #
        self.OptionParser.add_option("--fanned",         action="store", type='inkbool',
                                  dest="fanned",         default=False, help="Two scales on either side of the Neck")
        self.OptionParser.add_option("--basslength",     action="store", type="float",
                                  dest="basslength",     default=25.5, help="Length of the Bass side Scale")
        self.OptionParser.add_option("--perpendicular",  action="store", type="int",
                                  dest="perpendicular",  default=7, help="Fret number which is perpendicular to the Neck")
          
        #
        self.OptionParser.add_option("--linewidth",      action="store", type="float",
                                  dest="linewidth",      default=0.1, help="Width of drawn lines")
        self.OptionParser.add_option("--notch_width",    action="store", type="float",
                                  dest="notch_width",    default=0.125, help="Width of Fret notches on Router template")
        self.OptionParser.add_option("--annotate",       action="store", type='inkbool',
                                  dest="annotate",       default=True, help="Annotate with Markers etc")
        self.OptionParser.add_option("--centerline",     action="store", type='inkbool',
                                  dest="centerline",     default=True, help="Draw a centerline")
        # Neck
        self.OptionParser.add_option("--constant_width", action="store", type='inkbool',
                                  dest="constant_width", default=True, help="Use Bridge width as well to make Neck")
        self.OptionParser.add_option("--width_bridge",   action="store", type="float",
                                  dest="width_bridge",   default=2.0, help="Width at the Bridge (drawing Neck not Ruler)")
        self.OptionParser.add_option("--show_markers",   action="store", type='inkbool',
                                  dest="show_markers",   default=False, help="Show Neck Marker Positions")
        self.OptionParser.add_option('--markers',        action='store', type='string',
                                  dest='markers',        default='3,5,7,10,12,12,15', help="List of frets to draw markers on")
        #
        self.OptionParser.add_option("--nutcomp",        action="store", type='inkbool',
                                  dest="nutcomp",        default=False, help="Modify Nut position")
        self.OptionParser.add_option("--nutcomp_value",  action="store", type="string",
                                  dest="nutcomp_value",  default="0.012in (0.30mm)", help="Preset (usual) Nut compensation values")
        self.OptionParser.add_option("--nutcomp_manual", action="store", type="float",
                                  dest="nutcomp_manual", default=0.014, help="Manual distance to move Nut closer to Bridge")
        #
        self.OptionParser.add_option("--show_curves",    action="store", type='inkbool',
                                  dest="show_curves",    default=False, help="Show a neck curvature ruler")
        self.OptionParser.add_option("--neck_radius",    action="store", type="float",
                                  dest="neck_radius",    default=2.0, help="Radius of Neck curvature")
        self.OptionParser.add_option("--arc_length",     action="store", type="float",
                                  dest="arc_length",     default=2.0, help="Length of Arc")
        self.OptionParser.add_option("--block_mode",     action="store", type='inkbool',
                                  dest="block_mode",     default=False, help="Draw block or finger style")
        self.OptionParser.add_option("--arc_height",     action="store", type="float",
                                  dest="arc_height",     default=2.0, help="height of Arc")
        self.OptionParser.add_option("--string_spacing", action="store", type="float",
                                  dest="string_spacing", default=2.0, help="Spacing between strings")
        #
        self.OptionParser.add_option("--filter_tones",   action="store", type='inkbool',
                                  dest="filter_tones",   default=True, help="Only show Scala files with this many notes in a scale.")
        self.OptionParser.add_option("--scale",          action="store", type="int",
                                  dest="scale",          default=12, help="number of Notes in the scale")
        self.OptionParser.add_option("--filter_label",   action="store", type='inkbool',
                                  dest="filter_label",   default=True, help="Only show Scala files with this keyword in them.")
        self.OptionParser.add_option("--keywords",        action="store", type="string",
                                  dest="keywords",        default="diatonic", help="Keywords to search for")
        # here so we can have tabs
        self.OptionParser.add_option("", "--active-tab", 
                                     action="store", type="string",
                                     dest="active_tab", default='ruler', help="Active tab.")
    def getUnittouu(self, param):
        " compatibility between inkscape 0.48 and 0.91 "
        try:
            return inkex.unittouu(param)
        except AttributeError:
            return self.unittouu(param)

    def filter_scala_files(self, parent):
        """ Look in the scale directory for files.
            - show only files matching the filters
        """
        filter_tones = self.options.filter_tones
        filter_names = self.options.filter_label
        numtones = self.options.scale
        keywords = self.options.keywords
        keywords = keywords.strip().split(',')
        keywords = [k.lower() for k in keywords]
        #
        probable_dir = os.getcwd()+'/scales/'
        files = os.listdir(probable_dir)
        # inkex.debug("%s"%([os.getcwd(),len(files)]))
        # Display filenames in document
        filenames = [["Searched %d files"%(len(files)), "Found no matches", 0]]
        for f in files:
            fname = probable_dir+f
            data = fs.read_scala(fname, False)
            # filter out files that don't match
            if filter_tones and filter_names:
                if numtones == data[1]:
                    if filter_names:
                        for k in keywords:
                            if data[0].find(k) > -1 or f.find(k) > -1:
                                filenames.append([f, data[0], data[1]])
            elif filter_tones:
                if numtones == data[1]:
                    filenames.append([f, data[0], data[1]])
            elif filter_names:
                for k in keywords:
                    if data[0].find(k) > -1 or f.find(k) > -1:
                        filenames.append([f, data[0], data[1]])
        # inkex.debug("%s"%(filenames))
        # gathered them all - display them
        if len(filenames) != 0:
            filenames[0][1] = "Found %d matches"%(len(filenames)-1)
        x = 0
        y = 0
        Label_style['text-anchor'] = 'start'
        for f in filenames:
            label = f[0]
            if f[2] != 0:
                label += " - (%d tones)"%(f[2])
            self.draw_label(x, y, label, parent)
            self.draw_label(x+Font_height*2, y+Font_height*1.2, f[1], parent)
            if y ==0: y += Font_height
            y += Font_height*2.8
        Label_style['text-anchor'] = 'end'

###
    def draw_label(self, x,y, label, parent, transform=False, style=Label_style):
        " add a text entity "
        text_atts = {'style':simplestyle.formatStyle(style),
                     'x': str(x), 'y': str(y) }
        if transform: text_atts['transform'] = transform
        text = inkex.etree.SubElement(parent, 'text', text_atts)
        text.text = "%s" %(label)

###
    def draw_ruler(self, neck, parent, show_numbers=False):
        " draw the ruler with the centre of nut at 0,0 (unless fanned)"
        # fanned frets have a bass side as well as the normal(treble) side scale length
        # assume fanned 
        treble_length = neck.length
        bass_length = treble_length if not neck.fanned else neck.bass_scale
        y1 = neck.nut_width/2
        y2 = neck.bridge_width/2
        startx = 0
        endx = 0
        # if neck is fanned - adjust start, end
        if neck.fanned:
            if neck.fan_offset > 0:
                startx = neck.fan_offset
            else:
                endx = -neck.fan_offset
        pts = [[treble_length+startx,-y2], [bass_length+endx,y2], [endx,y1]]
        # Create the boundary(neck) paths
        path = 'M %s,%s ' % (startx*self.convFactor, -y1*self.convFactor)
        for i in range(3):
            path += " L %s,%s "%(pts[i][0]*self.convFactor, pts[i][1]*self.convFactor)
        path += "Z"
        line_attribs = {'style' : simplestyle.formatStyle(Line_style),
                        inkex.addNS('label','inkscape') : 'Outline' }
        line_attribs['d'] = path
        ell = inkex.etree.SubElement(parent, inkex.addNS('path','svg'), line_attribs )
        # Draw the fret lines
        distances = neck.frets # do the zeroth value as well
        for count, xt in enumerate(distances): # seq of x offsets for each fret
            xb = xt if not neck.fanned else neck.bass_frets[count]
            # if neck is not straight, calc the extra bit to draw in Y
            yt = yb = y1
            if y1 != y2: # neck not straight
                yt = y1 + ((xt-startx)/float(treble_length) * (y2-y1))
                yb = y1 + ((xb-endx)/float(bass_length) * (y2-y1))
            path = build_line([xt,-yt],[xb,yb], self.convFactor)
            line_attribs['d'] = path
            ell = inkex.etree.SubElement(parent, inkex.addNS('path','svg'), line_attribs)
            # Fret Numbers on odd frets(+octave)
            if show_numbers and (count%2 == 0 or count == neck.notes_in_scale-1):
                # try to push the lower fret numbers to the right a little
                Label_style['text-anchor'] = 'start' if count < 9 else 'middle'
                label_pos = neck.find_mid_point(count, -neck.nut_width/3)
                self.draw_label(label_pos[0]*self.convFactor, label_pos[1]*self.convFactor, count+1, parent)
                Label_style['text-anchor'] = 'end'

    def draw_router_template(self, neck, parent, notch_width, show_numbers=False):
        " draw the ruler as a notched router template "
        length = neck.length
        y = neck.nut_width/2
        startx = notch_width*6
        pts = [[length,-y], [length,y], [-startx,y]]
        path = 'M %s,%s ' % (-startx*self.convFactor, -y*self.convFactor) # start
        distances = [0]
        distances.extend(neck.frets)
        # style
        line_attribs = {'style' : simplestyle.formatStyle(Line_style),
                        inkex.addNS('label','inkscape') : 'Outline' }
        # draw the fret notches, lines, labels
        for count, x in enumerate(distances):
            path += build_notch(x,-y, notch_width, self.convFactor)
            if show_numbers and (count%2 == 1 or count == 0 or count == neck.notes_in_scale):
                Label_style['text-anchor'] = 'start' if count < 9 else 'middle'
                self.draw_label(x*self.convFactor-Font_height, -y*self.convFactor+Font_height*2.2, count, parent)
                Label_style['text-anchor'] = 'end'
            # other side markers
            path2 = build_line([x,y],[x,notch_width*2-y], self.convFactor)
            line_attribs['d'] = path2
            ell = inkex.etree.SubElement(parent, inkex.addNS('path','svg'), line_attribs)
        # close other side of template
        for i in range(3):
            path += " L %s,%s "%(pts[i][0]*self.convFactor, pts[i][1]*self.convFactor)
        path += "Z"
        # Draw
        line_attribs['d'] = path
        inkex.etree.SubElement(parent, inkex.addNS('path','svg'), line_attribs )

    def draw_neck_curve_ruler(self, neck, radius, arc_length, arc_height, string_spacing, parent):
        "  draw arcs for curved fretboards "
        # perfect world draw ruler and lines to curved ruler.
        # mode = 'block1'
        block_mode = self.options.block_mode
        tab_length = arc_height*3 * self.convFactor
        diam_in = radius * 2 * self.convFactor
        angle_d = 180*arc_length / (2*pi*radius)
        angle = radians(angle_d)
        dist = arc_height*self.convFactor
        path = "M%s %s L%s %s" %(diam_in + dist,0, diam_in,0)
        x_a = diam_in * cos(angle)
        y_a = diam_in * sin(angle)
        x_b = (diam_in + dist) * cos(angle)
        y_b = (diam_in + dist) * sin(angle)
        path += " A %s,%s 0 0 1 %s %s" % (diam_in, diam_in, x_a, y_a)
        path += " L%s %s" %(x_b, y_b)
        if block_mode:
            # use a solid block style
            # add a midpoint for users to play with
            path += " L%s %s" % (diam_in+dist+(x_b-diam_in-dist)/2, y_b/2)
            tab_length = 0
        else: # tab mode
            # need another arc with tab sections
            small_angle = radians(90*string_spacing / (2*pi*radius))
            angle2 = angle/2 + small_angle
            angle3 = angle/2 - small_angle
            x_c = (diam_in + dist) * cos(angle2)
            y_c = (diam_in + dist) * sin(angle2)
            x_d = (diam_in + dist + tab_length) * cos(angle2)
            y_d = (diam_in + dist + tab_length) * sin(angle2)
            x_e = (diam_in + dist + tab_length) * cos(angle3)
            y_e = (diam_in + dist + tab_length) * sin(angle3)
            x_f = (diam_in + dist) * cos(angle3)
            y_f = (diam_in + dist) * sin(angle3)
            path += " A %s,%s 0 0 0 %s %s" % (diam_in, diam_in, x_c, y_c)
            path += " L%s %s" %(x_d, y_d)
            path += " L%s %s" %(x_e, y_e)
            path += " L%s %s" %(x_f, y_f)
            path += " A %s,%s 0 0 0 %s %s" % (diam_in, diam_in, diam_in + dist, 0)
            
        # close path
        path += 'z'
        ypos = diam_in + dist + tab_length + self.options.width*self.convFactor
        line_attribs = {'style' : simplestyle.formatStyle(Line_style), inkex.addNS('label','inkscape') : 'Neck Curve',
                        'transform': 'rotate(%f) translate(%s,%s)' % (-angle_d/2 -90, -ypos,-dist)}
        line_attribs['d'] = path
        inkex.etree.SubElement(parent, inkex.addNS('path','svg'), line_attribs )
        # label
        size = "%d"%radius if radius-int(radius) == 0 else "%4.2f"%(radius)
        Label_style['text-anchor'] = 'start'
        self.draw_label(0, 0, "Radius: %s%s"% (size, neck.units), parent,
                        transform='translate(%s,%s)'%(0,ypos-diam_in-dist/2))
        Label_style['text-anchor'] = 'end'

    def draw_title(self, neck, parent, initial="Fret Ruler:"):
        " Draw list of labels far right of ruler/Neck "
        labels = [initial]
        length = "%d"%neck.length if neck.length-int(neck.length) == 0 else "%4.2f"%(neck.length)
        if neck.fanned:
            basslength = "%d"%neck.bass_scale if neck.bass_scale-int(neck.bass_scale) == 0 else "%4.2f"%(neck.bass_scale)
            labels.append("Scale(Fanned): %s%s - %s%s" %(length, neck.units, basslength, neck.units))
        else: # not fanned
            labels.append("Scale: %s%s, %d frets" %(length, neck.units, len(neck.frets)))
        #
        label2 = "Method: %s" % (neck.method.title())
        if neck.method == 'scala':
            label2 += " (%s) %d tones" %(neck.scala.split('/')[-1], len(neck.scala_notes))
            labels.append(label2)
            labels.append('"%s"' %(neck.description))
        else:
            labels.append(label2)
        # unit formatting
        units = self.options.units
        precision = 1 if units=='mm' else 2
        widthN = self.options.width
        widthB = self.options.width_bridge
        label_w = "{:4.{prec}f}{}".format(widthN, units, prec=precision)
        if not self.options.constant_width:
            label_w += "(Nut) - {:4.{prec}f}{}(Bridge)".format(widthB, units, prec=precision)
        labels.append("Width: %s"%(label_w))
        if not self.options.constant_width and len(neck.frets)>11:
            distance12 = neck.frets[11]
            # inkex.debug("%s"%([distance12/float(neck.length)]))
            width12 = widthN + (distance12/float(neck.length) * (widthB-widthN))
            labels.append("(at 12th fret: {:4.{prec}f}{})".format(width12, units, prec=precision))
        # where to draw
        starty = widthN if self.options.constant_width else widthB
        y = -starty/2*self.convFactor + Font_height*1.2
        x_offset = 0
        if neck.fanned and self.options.draw_style != 'template':
            x_offset = neck.fan_offset
        x = neck.length*self.convFactor - Font_height*1.5 + x_offset*self.convFactor
        # Draw
        for label in labels:
            self.draw_label(x,y, label, parent)
            y += Font_height*1.2

    def draw_nut_compensation(self, neck, distance, parent):
        " "
        # inkex.debug("%s"%([distance]))
        startx = 0
        endx = 0
        if neck.fanned:
            if neck.fan_offset > 0:
                startx = neck.fan_offset
            else:
                endx = -neck.fan_offset
        y = self.options.width/2
        path = build_line((startx+distance, -y), (endx+distance, y), self.convFactor)
        line_attribs = {'style' : simplestyle.formatStyle(Dash_style), 'd':path,
                        inkex.addNS('label','inkscape') : 'Nut Compensation' }
        inkex.etree.SubElement(parent, inkex.addNS('path','svg'), line_attribs)

    def draw_neck_markers(self, neck, parent):
        " draw symbol at fret pos. N possible "
        # list may contain several occurences of a fret - meaning draw dots equidistant
        positions = neck.frets
        try: # user input weirdness
            locations = self.options.markers.strip().split(",")
            counts = [[int(i),locations.count(i)] for i in locations if i]
            fret_counts = []
            for f in counts:
                if f not in fret_counts: fret_counts.append(f)
        except:
            inkex.errormsg("Could not parse list of fret numbers. E.g. 3,5,7,7")
            fret_counts = [[3,1]]
        # marker radius based on thinnest of the (to be marked) fret spacings
        spacings = [neck.frets[f-1] - neck.frets[max(0,f-2)] for f,c in fret_counts if f < len(neck.frets)+1]
        thinnest = min(spacings)
        marker_radius = thinnest/marker_rad_factor*self.convFactor
        for fret, count in fret_counts:
            if fret <= len(positions): # ignore if > #frets on this neck
                # inkex.debug("%s"%([fret,count,positions[fret]]))
                fret = fret-1
                if count == 1: # if odd, draw in center
                    markerpos = neck.find_mid_point(fret, 0)
                    draw_circle_marker(markerpos[0]*self.convFactor, markerpos[1]*self.convFactor, marker_radius, parent)
                else: # draw several at that fret
                    sep = neck.nut_width/float(count+2)
                    for i in range(count):
                        markerpos = neck.find_mid_point(fret, sep*i*2 - sep*(count-1))
                        draw_circle_marker(markerpos[0]*self.convFactor, markerpos[1]*self.convFactor, marker_radius, parent)


###
    def effect(self):
        # calc units conversion
        self.convFactor = self.getUnittouu("1" + self.options.units)
        # fix line width
        Line_style['stroke-width'] = self.getUnittouu(str(self.options.linewidth) + "mm")
        # Usually we want 12 tone octaves
        numtones = 12
        if self.options.method == 'Nroot2':
            numtones = int(self.options.nth)
            self.options.method = '%droot2'%(numtones)
        # Usually we don't want a scala file
        scala_filename=False
        if self.options.method == 'scala':
            scala_filename = "scales/"+self.options.scala_filename
            if scala_filename[-4:] != ".scl":
                scala_filename += ".scl"
        # Create group center of view
        t = 'translate(%s,%s)' % (self.view_center[0]-self.options.length*self.convFactor/2, self.view_center[1])
        grp_attribs = {inkex.addNS('label','inkscape'):'Fret Ruler', 'transform':t}
        grp = inkex.etree.SubElement(self.current_layer, 'g', grp_attribs)
        page = self.options.active_tab[1:-1]
        draw_style = self.options.draw_style
        # check if on Scala filters page
        if page == 'filters':
            # display filtered scala files
            self.filter_scala_files(grp)
        else: # Regular action of drawing a Ruler...
            # select which style to draw based on user choice and what page they're on...
            # if on Ruler page then use draw_style
            title = "Fret Ruler:"
            if page == 'neck': draw_style = 'neck'
            if page == 'ruler' and draw_style=='ruler' or draw_style=='template':
                # override constant width if on Ruler page
                self.options.constant_width = True
            # calc fret widths
            fret_width = self.options.width
            if (page == 'neck' or draw_style=='neck'):
                title = "Neck Ruler:"
                if not self.options.constant_width:
                    fret_width = [self.options.width, self.options.width_bridge]
            # Make the Neck
            neck = fs.Neck(self.options.length, units=self.options.units, fret_width=fret_width)
            neck.calc_fret_offsets(self.options.length, self.options.frets, self.options.method,
                                   numtones=numtones, scala_filename=scala_filename)
            if self.options.fanned:
                # fanned frets so calc bass scale and adjust
                perpendicular = min(self.options.perpendicular, len(neck.frets))
                off = neck.set_fanned(self.options.basslength, perpendicular)
            if  draw_style=='template':
                notch = self.options.notch_width
                title = "Router Template:"
                self.draw_router_template(neck, grp, notch, self.options.annotate)
            else:
                self.draw_ruler(neck, grp, self.options.annotate)
            self.draw_title(neck, grp, title)
            if self.options.centerline and self.options.draw_style != 'template':
                path = build_line((-0.5,0), (max(neck.length, neck.bass_scale)+0.5, 0), self.convFactor)
                line_attribs = {'style' : simplestyle.formatStyle(Centerline_style), 'd':path,
                                inkex.addNS('label','inkscape') : 'Centerline' }
                inkex.etree.SubElement(grp, inkex.addNS('path','svg'), line_attribs)
            # Neck specials
            if page == 'neck' or draw_style=='neck':
                # Nut compensation
                if self.options.nutcomp:
                    value = self.options.nutcomp_value
                    try:
                        compensation = float(value) if value != 'manual' else float(self.options.nutcomp_manual)
                        self.draw_nut_compensation(neck, compensation, grp)
                    except:
                        inkex.errormsg("Could not determine Nut compensation. Use a number.")
                # Markers
                if self.options.show_markers:
                    self.draw_neck_markers(neck, grp)
            # inkex.debug("#%s#"%(ordered_chords))
            if self.options.show_curves:
                # position below max height of title text
                self.draw_neck_curve_ruler(neck, self.options.neck_radius, self.options.arc_length, self.options.arc_height, self.options.string_spacing, grp)

        
        


# Create effect instance and apply it.
if __name__ == '__main__':
    Fret_ruler().affect()


### TODO:
# - draw option for fret0 hole to hang ruler from
# - draw strings
#   - how many strings
#   - separation distance
#   - work out interval offsets
# - calc bridge compensation
# - calc stretch compensation
# - draw side view with bridge, relief distances

#BUGS:
# 


# Links:
# Nut compensation: http://www.lmii.com/scale-length-intonation