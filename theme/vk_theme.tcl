# Copyright original theme © 2021 rdbende <rdbende@gmail.com>
# Copyright vk_theme © 2022 Mons <mons@mons.ws>



option add *tearOff 0

proc set_theme {mode} {
	if {$mode == "light"} {
		ttk::style theme use "vk_theme-light"

		array set colors {
            -fg             "#313131"
            -bg             "#EDEEF0"
		    -disabledfg     "#CACACA"
		    -selectfg       "#ffffff"
		    -selectbg       "#2f60d8"
		}

        ttk::style configure . \
            -background $colors(-bg) \
            -foreground $colors(-fg) \
            -troughcolor $colors(-bg) \
            -focuscolor $colors(-selectbg) \
            -selectbackground $colors(-selectbg) \
            -selectforeground $colors(-selectfg) \
            -insertwidth 1 \
            -insertcolor $colors(-fg) \
            -fieldbackground $colors(-selectbg) \
            -font {"Segoe Ui" 10} \
            -borderwidth 0 \
            -relief flat

        tk_setPalette background [ttk::style lookup . -background] \
            foreground [ttk::style lookup . -foreground] \
            highlightColor [ttk::style lookup . -focuscolor] \
            selectBackground [ttk::style lookup . -selectbackground] \
            selectForeground [ttk::style lookup . -selectforeground] \
            activeBackground [ttk::style lookup . -selectbackground] \
            activeForeground [ttk::style lookup . -selectforeground]
        
        ttk::style map . -foreground [list disabled $colors(-disabledfg)]

        option add *font [ttk::style lookup . -font]
        option add *Treeview.show tree
        option add *Menu.selectcolor $colors(-fg)
	}
}

package require Tk 8.6

namespace eval ttk::theme::vk_theme-light {
    variable version 1.0
    package provide ttk::theme::vk_theme-light $version

    ttk::style theme create vk_theme-light -parent clam -settings {
        proc load_images {imgdir} {
            variable images
            foreach file [glob -directory $imgdir *.png] {
                set images([file tail [file rootname $file]]) \
                [image create photo -file $file -format png]
            }
        }

        load_images [file join [file dirname [info script]] light]

        array set colors {
            -fg             "#313131"
            -bg             "#EDEEF0"
            -disabledfg     "#CACACA"
            -selectfg       "#ffffff"
            -selectbg       "#2f60d8"
        }
        ttk::style layout Accent.TButton {
            AccentButton.button -children {
                AccentButton.padding -children {
                    AccentButton.label -side left -expand 1
                } 
            }
        }
        
        ttk::style layout TLabelframe {
            Labelframe.border {
                Labelframe.padding -expand 1 -children {
                    Labelframe.label -side left
                }
            }
        }

        # Entry
        ttk::style configure TEntry -foreground $colors(-fg)
        ttk::style map TEntry -foreground \
            [list disabled #0a0a0a \
                pressed #636363 \
                active #626262
            ]

        ttk::style element create Entry.field \
            image [list $images(entry-rest) \
                {focus hover !invalid} $images(entry-focus) \
                invalid $images(entry-invalid) \
                disabled $images(entry-disabled) \
                {focus !invalid} $images(entry-focus) \
                hover $images(entry-hover) \
            ] -border 5 -padding {14 10} -sticky nsew 


        # Accent.TButton
        ttk::style configure Accent.TButton -padding {10 8} -anchor center -foreground $colors(-selectfg) -font {Verdana 12}

        ttk::style map Accent.TButton -foreground \
            [list disabled #1259B3 \
                pressed #FFF]

        ttk::style element create AccentButton.button image \
            [list $images(button-accent-rest) \
                {selected disabled} $images(button-accent-disabled) \
                disabled $images(button-accent-disabled) \
                selected $images(button-accent-rest) \
                pressed $images(button-accent-pressed) \
                active $images(button-accent-hover) \
            ] -border 4 -sticky nsew

        # Labelframe
        ttk::style element create Labelframe.border image $images(card) \
            -border 5 -padding 4 -sticky nsew
        
   
    }
}