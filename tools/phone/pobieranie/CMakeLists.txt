cmake_minimum_required(VERSION 3.20)
project(pobieranie LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_AUTOMOC ON)
set(CMAKE_AUTORCC ON)

find_package(Qt6 REQUIRED COMPONENTS Gui Qml Quick Network)

add_executable(pobieranie main.cpp pobieranie.qrc)
target_link_libraries(pobieranie PRIVATE Qt6::Gui Qt6::Qml Qt6::Quick Qt6::Network)
install(TARGETS pobieranie RUNTIME DESTINATION bin)
