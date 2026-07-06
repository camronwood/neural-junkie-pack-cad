/* [Dimensions] */
outer_x = 80;
outer_y = 50;
outer_z = 30;
wall = 2; // [1:5:0.5]

difference() {
  cube([outer_x, outer_y, outer_z]);
  translate([wall, wall, wall])
    cube([outer_x - 2 * wall, outer_y - 2 * wall, outer_z]);
}
